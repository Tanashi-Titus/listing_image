"""Dò DOM ảnh đã tạo trong 1 conversation để tìm selector tải ảnh đúng."""
from __future__ import annotations

import json
import sys

from core.browser import ChatGPTBrowser

CONV_URL = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else "probe2.json"


def main() -> None:
    br = ChatGPTBrowser(headless=False)
    br.start()
    br.page.goto(CONV_URL, wait_until="domcontentloaded")
    br.page.wait_for_timeout(6000)
    # cuộn xuống cuối để ảnh lazy-load
    for _ in range(4):
        br.page.mouse.wheel(0, 3000)
        br.page.wait_for_timeout(1200)
    br.page.wait_for_timeout(3000)

    info = br.page.evaluate(
        """() => {
        const imgs = [...document.querySelectorAll('img')].map(i => {
            let c = i.closest('[data-message-author-role]');
            let t = i.closest('[data-testid]');
            return {
                src: (i.currentSrc || i.src || '').slice(0, 100),
                alt: i.alt,
                nw: i.naturalWidth, nh: i.naturalHeight,
                role: c ? c.getAttribute('data-message-author-role') : null,
                testid: t ? t.getAttribute('data-testid') : null,
            };
        });
        // div co background-image (co the anh render kieu nay)
        const bg = [...document.querySelectorAll('*')].filter(e => {
            const b = getComputedStyle(e).backgroundImage;
            return b && b.includes('url(') && (b.includes('oaiusercontent') || b.includes('blob:'));
        }).map(e => ({ tag: e.tagName, bg: getComputedStyle(e).backgroundImage.slice(0,100) }));
        return { imgCount: imgs.length, imgs, bgImages: bg.slice(0,5) };
    }"""
    )
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(">> imgCount:", info["imgCount"], "bg:", len(info["bgImages"]), "->", OUT)
    br.close()


if __name__ == "__main__":
    main()
