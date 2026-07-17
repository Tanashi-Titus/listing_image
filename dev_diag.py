"""Chẩn đoán: thử tạo 1 ảnh, chụp lại đúng thứ ChatGPT hiển thị (ảnh / thông báo limit)."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from config import PRODUCT_DIR
from core.browser import ChatGPTBrowser
from core.chatgpt import ChatGPTSession

SHOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")


def main() -> None:
    br = ChatGPTBrowser(headless=False)
    br.start()
    br.open_chatgpt()
    if not br.is_logged_in(timeout_ms=15000):
        print(">> chua dang nhap")
        br.close()
        return
    gpt = ChatGPTSession(br.page)
    gpt.new_chat()
    gpt.upload_images([PRODUCT_DIR / "sp1.png"])
    gpt.type_prompt("Tạo 1 ảnh minh hoạ đơn giản từ sản phẩm này, nền trắng.")
    gpt.send()
    br.page.wait_for_timeout(20000)  # chờ 20s xem có gì hiện ra
    br.page.screenshot(path=str(SHOT / "diag_after_send.png"), full_page=True)
    # in text vùng main để bắt thông báo limit nếu có
    try:
        txt = br.page.inner_text("main")
        print(">> MAIN TEXT (2000 ky tu cuoi):")
        print(txt[-2000:])
    except Exception as e:
        print(">> loi doc text:", e)
    br.close()


if __name__ == "__main__":
    main()
