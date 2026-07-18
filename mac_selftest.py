"""
mac_selftest.py — Tự kiểm lớp license NGAY TRÊN runner macOS của GitHub Actions.

Không cần GUI, không cần máy Mac riêng. Kiểm đúng 2 thứ hay hỏng trên Mac:
  1. MÃ MÁY có ỔN ĐỊNH không khi PATH bị rút gọn (mô phỏng mở app bằng double-click
     qua Finder/launchd — lúc đó /usr/sbin KHÔNG có trong PATH).
  2. Toàn bộ luồng ký → verify_license_text → check_license có chạy đúng không
     (dùng cặp khoá tạm, KHÔNG đụng private key thật).

Chạy:  python mac_selftest.py   → in kết quả, exit != 0 nếu có lỗi (CI báo đỏ).
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import tnt_license as tl


def _fail(msg: str):
    print(f"❌ FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    print("== macOS license self-test ==")
    print("platform:", sys.platform)

    # --- 1) MÃ MÁY ổn định giữa "Terminal" (PATH đầy đủ) và "Finder" (PATH rút gọn) ---
    id_terminal = tl.get_machine_id()
    print("máy id (PATH đầy đủ)  :", tl.machine_id_pretty(id_terminal))

    # Phép rút PATH về /usr/bin:/bin chỉ có nghĩa trên macOS (mô phỏng launchd/Finder
    # không có /usr/sbin). Trên Windows nó sẽ làm hỏng powershell -> bỏ qua.
    if sys.platform == "darwin":
        full_path = os.environ.get("PATH", "")
        os.environ["PATH"] = "/usr/bin:/bin"
        try:
            id_finder = tl.get_machine_id()
        finally:
            os.environ["PATH"] = full_path
        print("máy id (PATH rút gọn):", tl.machine_id_pretty(id_finder))
        if id_terminal != id_finder:
            _fail(f"MÃ MÁY KHÔNG ổn định giữa Terminal và Finder:\n"
                  f"  {id_terminal}\n  {id_finder}\n"
                  f"→ license cấp theo mã này sẽ không khớp khi double-click.")
        print("✅ (1) mã máy ổn định ở cả 2 môi trường (Terminal & Finder)")
    else:
        print("ℹ️  (1) bỏ qua kiểm PATH-strip (chỉ chạy trên macOS)")

    # --- 2) Luồng ký → verify → check_license (khoá TẠM, không dùng private key thật) ---
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    priv = Ed25519PrivateKey.generate()
    pub_hex = priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    tl.PUBLIC_KEY_HEX = pub_hex   # tráo public key sang khoá tạm cho bài test

    payload = {
        "machine_id": id_terminal,
        "expires": None,
        "tools": None,
        "issued": date.today().isoformat(),
        "note": "ci-selftest",
    }
    sig = priv.sign(tl._canonical_payload_bytes(payload))
    lic_text = tl.encode_license(payload, sig)

    # 2a) verify trực tiếp
    try:
        info = tl.verify_license_text(lic_text, "TNT_Listing", this_machine_id=id_terminal)
    except Exception as e:
        _fail(f"verify_license_text lỗi: {e}")
    print("✅ (2a) verify_license_text OK:", info)

    # 2b) check_license đọc từ FILE license.key đặt qua TNT_LICENSE_PATH
    tmp = Path("ci_license.key")
    tmp.write_text(lic_text, encoding="utf-8")
    os.environ["TNT_LICENSE_PATH"] = str(tmp.resolve())
    try:
        info2 = tl.check_license("TNT_Listing", raise_on_error=True)
    except Exception as e:
        _fail(f"check_license lỗi: {e}")
    finally:
        tmp.unlink(missing_ok=True)
    print("✅ (2b) check_license OK:", info2)

    # 2c) license SAI máy phải bị từ chối
    try:
        tl.verify_license_text(lic_text, "TNT_Listing", this_machine_id="0" * 64)
        _fail("license sai máy đáng lẽ phải bị từ chối mà lại pass!")
    except tl.LicenseError:
        print("✅ (2c) license sai máy bị từ chối đúng")

    print("\n🎉 TẤT CẢ PASS — lớp license chạy đúng trên macOS.")


if __name__ == "__main__":
    main()
