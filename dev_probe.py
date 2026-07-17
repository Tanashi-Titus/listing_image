"""Script THĂM DÒ (dev) — không gửi gì, chỉ mở ChatGPT & in cấu trúc DOM.

Mục đích: xác định chính xác selector hiện tại của ChatGPT cho:
  - ô nhập prompt
  - input upload file
  - nút gửi
Rồi chụp màn hình để kiểm tra.
"""
from __future__ import annotations

import json
import sys

from core.browser import ChatGPTBrowser

SHOT_DIR = sys.argv[1] if len(sys.argv) > 1 else "."


def main() -> None:
    br = ChatGPTBrowser(headless=False)
    br.start()
    br.open_chatgpt()

    page = br.page
    print(">> URL:", page.url)

    logged = br.is_logged_in(timeout_ms=20000)
    print(">> logged_in:", logged)
    if not logged:
        print(">> CHUA dang nhap — dang cho login toi da 5 phut...")
        logged = br.wait_for_login()
        print(">> logged_in sau khi cho:", logged)
    if not logged:
        br.close()
        return

    page.wait_for_timeout(2000)

    info = page.evaluate(
        """() => {
        const out = {};

        // ô nhập prompt
        const composer = document.querySelector('#prompt-textarea');
        out.composer = composer ? {
            tag: composer.tagName,
            contenteditable: composer.getAttribute('contenteditable'),
            cls: composer.className.slice(0,120),
        } : null;

        // tat ca input file
        out.fileInputs = [...document.querySelectorAll('input[type=file]')].map(i => ({
            accept: i.accept,
            multiple: i.multiple,
            name: i.name,
            hidden: i.offsetParent === null,
        }));

        // cac nut co the la nut gui / dinh kem
        const btns = [...document.querySelectorAll('button')];
        out.buttons = btns.map(b => ({
            testid: b.getAttribute('data-testid'),
            aria: b.getAttribute('aria-label'),
            title: b.getAttribute('title'),
        })).filter(b => b.testid || b.aria || b.title)
          .filter(b => /send|attach|file|upload|image|gui|dinh|plus|add/i.test(
              (b.testid||'')+(b.aria||'')+(b.title||'')));

        return out;
    }"""
    )
    out_json = f"{SHOT_DIR}/probe_dom.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(">> DOM info ghi ra:", out_json)

    shot = f"{SHOT_DIR}/probe_composer.png"
    page.screenshot(path=shot)
    print(">> screenshot:", shot)

    br.close()


if __name__ == "__main__":
    main()
