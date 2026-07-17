"""Thao tác ChatGPT web ASYNC trên 1 tab (Page).

Port từ core/chatgpt.py (bản sync đã kiểm chứng). Selector giữ nguyên.
"""
from __future__ import annotations

import asyncio
import base64
import time
from pathlib import Path
from typing import List, Optional

from playwright.async_api import Page, TimeoutError as PWTimeout

from config import CHATGPT_URL

SEL_COMPOSER = "#prompt-textarea"
SEL_FILE_INPUT = 'input[type="file"]'
SEL_SEND_BTN = '[data-testid="send-button"]'
SEL_STOP_BTN = (
    'button[data-testid="stop-button"], button[aria-label*="Stop streaming"], '
    'button[aria-label*="Dừng"], button[aria-label*="Ngừng"]'
)


class StopRequested(Exception):
    """User bấm Dừng."""


class AioSession:
    """Bọc 1 tab đã đăng nhập để thao tác tạo ảnh / hỏi text."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.cancel = None   # threading.Event — set khi user bấm Dừng

    def _stop(self):
        if self.cancel is not None and self.cancel.is_set():
            raise StopRequested()

    # ------------------------------------------------------------------ #
    async def new_chat(self) -> None:
        await self.page.goto(CHATGPT_URL, wait_until="domcontentloaded")
        await self.page.wait_for_selector(SEL_COMPOSER, timeout=30000)
        await self.page.wait_for_timeout(800)

    async def open_conversation(self, url: str) -> None:
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(SEL_COMPOSER, timeout=30000)
        for _ in range(3):
            await self.page.mouse.wheel(0, 2500)
            await self.page.wait_for_timeout(800)
        await self.page.wait_for_timeout(1000)

    # ------------------------------------------------------------------ #
    async def upload_images(self, paths: List[Path], timeout_ms: int = 60000) -> int:
        paths = [str(Path(p)) for p in paths]
        before = await self._count_thumbnails()
        await self.page.locator(SEL_FILE_INPUT).first.set_input_files(paths)
        target = before + len(paths)
        deadline = time.time() + timeout_ms / 1000
        while time.time() < deadline:
            if await self._count_thumbnails() >= target:
                await self.page.wait_for_timeout(1500)
                return await self._count_thumbnails()
            await self.page.wait_for_timeout(700)
        return await self._count_thumbnails()

    async def _count_thumbnails(self) -> int:
        try:
            return await self.page.evaluate(
                "() => document.querySelectorAll('img[src^=\"blob:\"]').length"
            )
        except Exception:
            return 0

    # ------------------------------------------------------------------ #
    async def type_prompt(self, text: str) -> None:
        """Nhập prompt vào ô ProseMirror bằng sự kiện PASTE tổng hợp.

        Gõ từng phím / insert_text bị ProseMirror xáo trộn khi text dài. Bắn
        1 sự kiện 'paste' với DataTransfer → ProseMirror chèn đồng bộ 1 lần,
        chính xác, không cần quyền clipboard. Có kiểm tra + fallback.
        """
        clean = " ".join(text.split())
        await self.page.locator(SEL_COMPOSER).click()
        await self.page.evaluate(
            """(text) => {
                const el = document.querySelector('#prompt-textarea');
                if (!el) return;
                el.focus();
                const dt = new DataTransfer();
                dt.setData('text/plain', text);
                el.dispatchEvent(new ClipboardEvent('paste',
                    {clipboardData: dt, bubbles: true, cancelable: true}));
            }""",
            clean,
        )
        await self.page.wait_for_timeout(300)
        # kiểm tra, nếu lệch thì thử lại bằng insert_text
        got = await self.page.evaluate(
            "() => (document.querySelector('#prompt-textarea')||{}).innerText || ''"
        )
        if " ".join(got.split()) != clean:
            await self.page.evaluate(
                "() => { const e=document.querySelector('#prompt-textarea');"
                " if(e){e.focus();document.execCommand('selectAll',false,null);} }"
            )
            await self.page.keyboard.press("Delete")
            await self.page.keyboard.insert_text(clean)

    async def send(self) -> None:
        btn = self.page.locator(SEL_SEND_BTN)
        try:
            await btn.wait_for(state="visible", timeout=5000)
            await btn.click()
            return
        except PWTimeout:
            pass
        await self.page.locator(SEL_COMPOSER).click()
        await self.page.keyboard.press("Enter")

    # ------------------------------------------------------------------ #
    async def ask_text(self, prompt: str, timeout_ms: int = 120000) -> str:
        """Gửi 1 message text, chờ tới khi text NGỪNG TĂNG độ dài (~3.6s) thì lấy.

        KHÔNG phụ thuộc nút 'Dừng' (dễ dương tính giả gây chờ hết timeout).
        """
        self._stop()
        await self.type_prompt(prompt)
        await self.send()
        await self.page.wait_for_timeout(1500)

        end = time.time() + timeout_ms / 1000
        last_len = -1
        stable = 0
        text = ""
        while time.time() < end:
            self._stop()
            text = await self._last_assistant_text()
            cur = len(text or "")
            if cur > 0 and cur == last_len:
                stable += 1
                if stable >= 3:          # text ổn định ~3.6s → xong
                    return text
            else:
                stable = 0
                last_len = cur
            await self.page.wait_for_timeout(1200)
        return text

    async def _assistant_count(self) -> int:
        try:
            return await self.page.evaluate(
                "() => document.querySelectorAll("
                "'[data-message-author-role=\"assistant\"]').length"
            )
        except Exception:
            return 0

    async def _last_assistant_text(self, min_before: int = 0) -> str:
        try:
            return await self.page.evaluate(
                """() => {
                    const els = [...document.querySelectorAll(
                        '[data-message-author-role="assistant"]')];
                    if (!els.length) return "";
                    return els[els.length - 1].innerText || "";
                }"""
            )
        except Exception:
            return ""

    async def _wait_generation_done(self, timeout_ms: int = 120000,
                                    poll_ms: int = 1000) -> None:
        """Chờ đến khi ChatGPT ngừng sinh (nút Dừng biến mất, ổn định)."""
        deadline = time.time() + timeout_ms / 1000
        await self._wait_generation_started(max_s=12)
        gone = 0
        while time.time() < deadline:
            if not await self._is_generating():
                gone += 1
                if gone >= 2:
                    return
            else:
                gone = 0
            await self.page.wait_for_timeout(poll_ms)

    # ------------------------------------------------------------------ #
    async def generated_srcs(self) -> List[str]:
        try:
            return await self.page.evaluate(
                """() => {
                    const seen = new Set(); const out = [];
                    for (const i of document.querySelectorAll(
                        '[data-testid^="conversation-turn"] img')) {
                        if (/auth0|avatars/.test(i.src)) continue;
                        if (i.closest('[data-message-author-role="user"]')) continue;
                        if (i.naturalWidth <= 200 || i.naturalHeight <= 200) continue;
                        const s = i.currentSrc || i.src;
                        if (!seen.has(s)) { seen.add(s); out.push(s); }
                    }
                    return out;
                }"""
            )
        except Exception:
            return []

    async def wait_for_image(self, timeout_ms: int = 180000, poll_ms: int = 2000,
                             baseline: Optional[set] = None) -> Optional[str]:
        base = set(baseline or ())
        deadline = time.time() + timeout_ms / 1000
        await self._wait_generation_started(max_s=10, base=base)
        last_new = None
        stable = 0
        while time.time() < deadline:
            self._stop()
            generating = await self._is_generating()
            new = [s for s in await self.generated_srcs() if s not in base]
            cur = new[-1] if new else None
            if cur:
                if cur == last_new:
                    stable += 1
                else:
                    stable = 0
                    last_new = cur
                if not generating or stable >= 2:
                    return cur
            await self.page.wait_for_timeout(poll_ms)
        return last_new

    async def _wait_generation_started(self, max_s: int = 10, base=None) -> None:
        end = time.time() + max_s
        while time.time() < end:
            self._stop()
            if await self._is_generating():
                return
            if base is not None:  # ảnh mới đã xuất hiện rồi thì thôi chờ
                if any(s not in base for s in await self.generated_srcs()):
                    return
            await self.page.wait_for_timeout(500)

    async def _is_generating(self) -> bool:
        """Chỉ tính nút Dừng ĐANG HIỂN THỊ (tránh dương tính giả do nút ẩn)."""
        try:
            return await self.page.evaluate(
                """(sel) => {
                    for (const b of document.querySelectorAll(sel)) {
                        const r = b.getBoundingClientRect();
                        const st = getComputedStyle(b);
                        if (r.width > 0 && r.height > 0 &&
                            st.visibility !== 'hidden' && st.display !== 'none')
                            return true;
                    }
                    return false;
                }""",
                SEL_STOP_BTN,
            )
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    async def download_image(self, src: str, dest: Path) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.startswith("http"):
            try:
                resp = await self.page.context.request.get(src, timeout=60000)
                if resp.ok:
                    dest.write_bytes(await resp.body())
                    return dest
            except Exception:
                pass
        data_url = await self.page.evaluate(
            """async (src) => {
                const r = await fetch(src);
                const b = await r.blob();
                return await new Promise(res => {
                    const fr = new FileReader();
                    fr.onload = () => res(fr.result);
                    fr.readAsDataURL(b);
                });
            }""",
            src,
        )
        dest.write_bytes(base64.b64decode(data_url.split(",", 1)[1]))
        return dest

    async def refine(self, prompt: str, extra_images=None,
                     timeout_ms: int = 240000):
        """Sửa ảnh trong cuộc chat ĐANG MỞ: gửi prompt sửa (+ ảnh tham chiếu),
        chờ ảnh MỚI. Trả src ảnh mới hoặc None."""
        baseline = set(await self.generated_srcs())
        if extra_images:
            await self.upload_images([Path(p) for p in extra_images])
        await self.type_prompt(prompt)
        await self.send()
        await self.page.wait_for_timeout(2000)
        return await self.wait_for_image(timeout_ms=timeout_ms, baseline=baseline)

    def conversation_url(self) -> str:
        return self.page.url
