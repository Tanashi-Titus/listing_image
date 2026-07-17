"""Các thao tác trên ChatGPT web: tạo chat, upload ảnh, gửi prompt, chờ ảnh, tải ảnh.

Toàn bộ selector gom ở đây để khi ChatGPT đổi giao diện chỉ sửa 1 chỗ.
Module không phụ thuộc UI — nhận 1 Page của Playwright rồi thao tác.
"""
from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import List, Optional

from playwright.sync_api import Page, TimeoutError as PWTimeout

from config import CHATGPT_URL

# --- Selector (sửa ở đây nếu ChatGPT đổi giao diện) ------------------------
SEL_COMPOSER = "#prompt-textarea"
SEL_FILE_INPUT = 'input[type="file"]'
SEL_SEND_BTN = '[data-testid="send-button"]'
# nút dừng khi đang sinh (nhiều biến thể ngôn ngữ)
SEL_STOP_BTN = (
    'button[data-testid="stop-button"], button[aria-label*="Stop"], '
    'button[aria-label*="Dừng"], button[aria-label*="Ngừng"]'
)


class ChatGPTSession:
    """Bọc 1 Page đã đăng nhập để thao tác tạo ảnh."""

    def __init__(self, page: Page) -> None:
        self.page = page

    # ------------------------------------------------------------------ #
    def new_chat(self) -> None:
        """Về trang chat mới sạch."""
        self.page.goto(CHATGPT_URL, wait_until="domcontentloaded")
        self.page.wait_for_selector(SEL_COMPOSER, timeout=30000)
        self.page.wait_for_timeout(800)

    def open_conversation(self, url: str) -> None:
        """Mở lại 1 cuộc chat cũ (để tinh chỉnh). Cuộn để nạp ảnh sẵn có."""
        self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_selector(SEL_COMPOSER, timeout=30000)
        # cuộn xuống để ảnh cũ lazy-load (cần cho baseline chính xác)
        for _ in range(3):
            self.page.mouse.wheel(0, 2500)
            self.page.wait_for_timeout(800)
        self.page.wait_for_timeout(1200)

    # ------------------------------------------------------------------ #
    def upload_images(self, paths: List[Path], timeout_ms: int = 60000) -> int:
        """Đính kèm nhiều ảnh vào ô soạn. Trả về số thumbnail nhìn thấy."""
        paths = [str(Path(p)) for p in paths]

        before = self._count_thumbnails()
        # set_input_files hoạt động cả với input ẩn.
        file_input = self.page.locator(SEL_FILE_INPUT).first
        file_input.set_input_files(paths)

        # chờ thumbnail xuất hiện đủ (đã upload xong)
        target = before + len(paths)
        deadline = time.time() + timeout_ms / 1000
        while time.time() < deadline:
            now = self._count_thumbnails()
            if now >= target:
                # chờ thêm để chắc chắn upload xong (hết spinner)
                self.page.wait_for_timeout(1500)
                return now
            self.page.wait_for_timeout(700)
        return self._count_thumbnails()

    def _count_thumbnails(self) -> int:
        """Đếm ảnh preview blob: đang đính kèm trong khung soạn."""
        try:
            return self.page.evaluate(
                "() => document.querySelectorAll('img[src^=\"blob:\"]').length"
            )
        except Exception:
            return 0

    # ------------------------------------------------------------------ #
    def type_prompt(self, text: str) -> None:
        """Nhập prompt vào ô ProseMirror bằng sự kiện PASTE tổng hợp.

        Gõ từng phím / insert_text bị ProseMirror xáo trộn khi text dài. Bắn 1
        sự kiện 'paste' với DataTransfer → chèn đồng bộ 1 lần, chính xác.
        """
        clean = " ".join(text.split())
        self.page.locator(SEL_COMPOSER).click()
        self.page.evaluate(
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
        self.page.wait_for_timeout(300)

    # ------------------------------------------------------------------ #
    def send(self) -> None:
        """Bấm nút gửi; nếu không có thì Enter."""
        btn = self.page.locator(SEL_SEND_BTN)
        try:
            btn.wait_for(state="visible", timeout=5000)
            btn.click()
            return
        except PWTimeout:
            pass
        # fallback
        self.page.locator(SEL_COMPOSER).click()
        self.page.keyboard.press("Enter")

    # ------------------------------------------------------------------ #
    def generated_srcs(self) -> List[str]:
        """Danh sách src các ảnh ChatGPT ĐÃ TẠO (đã load đủ), theo thứ tự.

        Lọc: trong 1 conversation-turn, không phải avatar, không phải ảnh
        user upload (role=user), kích thước thật đủ lớn. Bỏ trùng src.
        """
        try:
            return self.page.evaluate(
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

    def wait_for_image(
        self,
        timeout_ms: int = 240000,
        poll_ms: int = 2000,
        baseline: Optional[set] = None,
    ) -> Optional[str]:
        """Chờ ChatGPT tạo xong 1 ảnh MỚI. Trả về src, hoặc None.

        - baseline: tập src ảnh đã có TRƯỚC khi gửi. Chỉ coi là "mới" nếu
          src không nằm trong baseline. Tạo mới thì để None (baseline rỗng).
        - Xong khi: có ảnh mới load đủ VÀ (không còn đang sinh HOẶC src mới
          giữ nguyên qua 2 lần kiểm tra — phòng khi không bắt được nút Dừng).
        """
        base = set(baseline or ())
        deadline = time.time() + timeout_ms / 1000
        self._wait_generation_started(max_s=20)

        last_new = None
        stable = 0
        while time.time() < deadline:
            generating = self._is_generating()
            new = [s for s in self.generated_srcs() if s not in base]
            cur = new[-1] if new else None
            if cur:
                if cur == last_new:
                    stable += 1
                else:
                    stable = 0
                    last_new = cur
                if not generating or stable >= 2:
                    return cur
            self.page.wait_for_timeout(poll_ms)
        return last_new

    def _wait_generation_started(self, max_s: int = 15) -> None:
        end = time.time() + max_s
        while time.time() < end:
            if self._is_generating():
                return
            self.page.wait_for_timeout(500)

    def _is_generating(self) -> bool:
        try:
            return self.page.locator(SEL_STOP_BTN).count() > 0
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    def download_image(self, src: str, dest: Path) -> Path:
        """Tải ảnh về đĩa.

        Ưu tiên tải qua network stack của trình duyệt (context.request) — KHÔNG
        nạp ảnh vào JS heap nên nhẹ, tránh làm renderer hết RAM (gây crash tab
        khi chat chung có nhiều ảnh lớn). Fallback: fetch base64 trong trang
        (cần cho src dạng blob:).
        """
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)

        if src.startswith("http"):
            try:
                resp = self.page.context.request.get(src, timeout=60000)
                if resp.ok:
                    dest.write_bytes(resp.body())
                    return dest
            except Exception:
                pass  # rơi xuống fallback

        # Fallback (blob: hoặc khi cách trên lỗi)
        data_url = self.page.evaluate(
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
        b64 = data_url.split(",", 1)[1]
        dest.write_bytes(base64.b64decode(b64))
        return dest

    # ------------------------------------------------------------------ #
    def refine(
        self,
        prompt: str,
        extra_images: Optional[List[Path]] = None,
        timeout_ms: int = 240000,
    ) -> Optional[str]:
        """Gửi 1 lượt tinh chỉnh trên cuộc chat ĐANG MỞ. Trả về src ảnh mới.

        - prompt: yêu cầu sửa (vd: "đổi nền sang màu be, sáng hơn").
        - extra_images: ảnh tham chiếu thêm nếu muốn (có thể None).
        Ảnh đã tạo trước đó ChatGPT vẫn nhớ trong ngữ cảnh nên không cần gửi lại.
        """
        baseline = set(self.generated_srcs())
        if extra_images:
            self.upload_images([Path(p) for p in extra_images])
        self.type_prompt(prompt)
        self.send()
        return self.wait_for_image(timeout_ms=timeout_ms, baseline=baseline)

    # ------------------------------------------------------------------ #
    def conversation_url(self) -> str:
        """URL cuộc chat hiện tại (để sau này quay lại tinh chỉnh)."""
        return self.page.url
