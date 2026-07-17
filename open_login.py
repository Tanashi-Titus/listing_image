"""Mở Chrome cho user đăng nhập 1 profile, TỰ nhận biết login xong rồi đóng.

Không dùng input() để chạy nền được.
    python open_login.py [profile_name]
"""
from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from core.browser import ChatGPTBrowser
from config import profile_path

name = sys.argv[1] if len(sys.argv) > 1 else "acc2"


def main() -> None:
    pdir = profile_path(name)
    br = ChatGPTBrowser(profile_dir=pdir)
    print(f">> Mở Chrome, profile: {name} ({pdir.name})", flush=True)
    br.start()
    # điều hướng có retry (trang mới đôi khi ERR_ABORTED lần đầu)
    for attempt in range(4):
        try:
            br.open_chatgpt()
            break
        except Exception as e:
            print(f">> nav lần {attempt+1} lỗi: {repr(e)[:80]} — thử lại...", flush=True)
            br.page.wait_for_timeout(1500)

    if br.is_logged_in(timeout_ms=6000):
        print(">> Profile này ĐÃ đăng nhập sẵn.", flush=True)
        br.page.wait_for_timeout(3000)
        br.close()
        return

    print(">> Hãy ĐĂNG NHẬP ChatGPT trong cửa sổ vừa mở (chờ tối đa 10 phút)...",
          flush=True)
    ok = br.wait_for_login(poll_seconds=3, max_wait_seconds=600)
    if ok:
        print(">> ✓ ĐÃ ĐĂNG NHẬP — đang lưu session...", flush=True)
        br.page.wait_for_timeout(4000)  # đảm bảo cookie ghi xong
        print(f">> ✓ Session lưu vào {pdir.name}/. Xong.", flush=True)
    else:
        print(">> ✗ Hết thời gian chờ, chưa đăng nhập.", flush=True)
    br.close()


if __name__ == "__main__":
    main()
