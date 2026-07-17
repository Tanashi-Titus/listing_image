"""Test tinh chỉnh (GĐ4): mở lại chat cũ, gửi prompt sửa, tải ảnh mới v2.

Chạy:
    python test_refine.py "<conversation_url>" "<prompt sửa>" [thu_muc_shot]
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from config import OUTPUT_DIR
from core.browser import ChatGPTBrowser
from core.chatgpt import ChatGPTSession

CONV_URL = sys.argv[1]
REFINE_PROMPT = sys.argv[2] if len(sys.argv) > 2 else (
    "Giữ nguyên người mẫu và sản phẩm, nhưng đổi phông nền sang tông màu be ấm, "
    "thêm bóng đổ nhẹ cho sản phẩm nổi khối hơn."
)
SHOT = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(".")


def log(m: str) -> None:
    print(f">> {m}", flush=True)


def main() -> None:
    br = ChatGPTBrowser(headless=False)
    br.start()
    gpt = ChatGPTSession(br.page)
    try:
        log("Mở lại chat cũ...")
        gpt.open_conversation(CONV_URL)

        base = gpt.generated_srcs()
        log(f"Ảnh đã có sẵn (baseline): {len(base)}")
        br.page.screenshot(path=str(SHOT / "r1_opened.png"))

        log(f"Gửi prompt sửa: {REFINE_PROMPT[:50]}...")
        src = gpt.refine(REFINE_PROMPT)  # tự baseline + chờ ảnh mới
        br.page.screenshot(path=str(SHOT / "r2_done.png"))
        log(f"Ảnh mới src: {str(src)[:80] if src else None}")

        if src and src not in set(base):
            dest = OUTPUT_DIR / "test" / "v2.png"
            gpt.download_image(src, dest)
            log(f"✓ ĐÃ TẢI ảnh tinh chỉnh: {dest} ({Path(dest).stat().st_size} bytes)")
        elif src:
            log("✗ src trùng ảnh cũ — chưa nhận ra ảnh mới.")
        else:
            log("✗ Không thấy ảnh mới — xem r2_done.png.")

        log(f"URL: {gpt.conversation_url()}")
    except Exception as e:
        log(f"LỖI: {e!r}")
        try:
            br.page.screenshot(path=str(SHOT / "r_error.png"))
        except Exception:
            pass
    finally:
        br.page.wait_for_timeout(1500)
        br.close()


if __name__ == "__main__":
    main()
