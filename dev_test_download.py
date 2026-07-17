"""Test lấy src + tải ảnh trên 1 conversation đã có sẵn ảnh (không tạo mới)."""
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


def main() -> None:
    br = ChatGPTBrowser(headless=False)
    br.start()
    br.page.goto(CONV_URL, wait_until="domcontentloaded")
    br.page.wait_for_timeout(5000)
    for _ in range(3):
        br.page.mouse.wheel(0, 3000)
        br.page.wait_for_timeout(1000)

    gpt = ChatGPTSession(br.page)
    src = None
    for i in range(20):  # poll toi da ~40s
        src = gpt._last_ready_image_src()
        if src:
            print(f">> thay anh sau {i} lan poll")
            break
        br.page.mouse.wheel(0, 1500)
        br.page.wait_for_timeout(2000)
    print(">> src:", str(src)[:90] if src else None)
    if src:
        dest = OUTPUT_DIR / "test" / "v1.png"
        gpt.download_image(src, dest)
        p = Path(dest)
        print(f">> ✓ TẢI XONG: {dest} ({p.stat().st_size} bytes)")
    else:
        print(">> ✗ vẫn không thấy ảnh")
    br.close()


if __name__ == "__main__":
    main()
