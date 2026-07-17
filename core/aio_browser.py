"""Trình duyệt Playwright ASYNC — 1 profile, nhiều TAB chạy song song.

Async để có thể lái nhiều tab ChatGPT cùng lúc (asyncio.gather) → tạo ảnh
song song, nhanh hơn nhiều so với tuần tự. Selector/logic port từ bản sync
đã kiểm chứng thực chiến (20/20 ảnh).
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from playwright.async_api import (
    async_playwright,
    BrowserContext,
    Page,
    TimeoutError as PWTimeout,
)

from config import PROFILE_DIR, CHATGPT_URL, SELECTOR_COMPOSER


def _centered_window_args(w: int = 1180, h: int = 840):
    """Tính vị trí căn GIỮA màn hình cho cửa sổ Chrome (Windows)."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        return [f"--window-position={x},{y}", f"--window-size={w},{h}"]
    except Exception:
        return [f"--window-size={w},{h}"]


class AioBrowser:
    """Vòng đời 1 trình duyệt async dùng chung profile đăng nhập."""

    def __init__(self, profile_dir: Path = PROFILE_DIR, headless: bool = False,
                 hidden: bool = False):
        # headless: ẩn hẳn (ChatGPT CHẶN — Cloudflare) → tránh dùng.
        # hidden : chạy trình duyệt THẬT nhưng đặt cửa sổ ra ngoài màn hình
        #          (chạy ngầm, không che, vẫn qua được Cloudflare).
        self.profile_dir = Path(profile_dir)
        self.headless = headless
        self.hidden = hidden
        self._pw = None
        self.context: Optional[BrowserContext] = None

    async def start(self) -> BrowserContext:
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._cleanup_profile_lock()
        self._pw = await async_playwright().start()

        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
        ]
        if self.hidden and not self.headless:
            # đẩy cửa sổ ra ngoài vùng nhìn thấy
            args += ["--window-position=-2400,-2400", "--window-size=1280,900"]
        elif not self.headless:
            # cửa sổ HIỆN (vd đăng nhập) → căn GIỮA màn hình
            args += _centered_window_args(1180, 840)

        kwargs = dict(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            viewport={"width": 1280, "height": 900},
            args=args,
        )
        self.context = await self._launch_with_retry(kwargs)
        await self.context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        # cấp quyền clipboard để dán prompt nguyên khối (tránh xáo trộn ký tự)
        try:
            await self.context.grant_permissions(
                ["clipboard-read", "clipboard-write"], origin="https://chatgpt.com"
            )
        except Exception:
            pass
        return self.context

    async def _launch_with_retry(self, kwargs: dict) -> BrowserContext:
        async def _do():
            try:
                return await self._pw.chromium.launch_persistent_context(
                    channel="chrome", **kwargs
                )
            except Exception as e:
                if "existing browser session" in str(e).lower():
                    raise
                return await self._pw.chromium.launch_persistent_context(**kwargs)

        try:
            return await _do()
        except Exception as e:
            if "existing browser session" in str(e).lower():
                self._kill_profile_chrome()
                self._cleanup_profile_lock()
                return await _do()
            raise

    async def new_page(self) -> Page:
        assert self.context is not None
        return await self.context.new_page()

    async def first_page(self) -> Page:
        assert self.context is not None
        pages = self.context.pages
        return pages[0] if pages else await self.context.new_page()

    async def open_chatgpt(self, page: Page) -> None:
        await page.goto(CHATGPT_URL, wait_until="domcontentloaded")

    async def is_logged_in(self, page: Page = None, timeout_ms: int = 8000) -> bool:
        """True nếu ĐÃ đăng nhập thật — kiểm cookie session-token (chắc chắn)."""
        if self.context is None:
            return False
        try:
            cookies = await self.context.cookies("https://chatgpt.com/")
        except Exception:
            return False
        return any(
            c.get("name", "").startswith("__Secure-next-auth.session-token")
            for c in cookies
        )

    async def close(self) -> None:
        try:
            if self.context is not None:
                await self.context.close()
        except Exception:
            pass  # context/trình duyệt có thể đã chết — bỏ qua
        finally:
            try:
                if self._pw is not None:
                    await self._pw.stop()
            except Exception:
                pass
            self.context = None
            self._pw = None

    # --- dọn lock (giống bản sync) ------------------------------------ #
    def _cleanup_profile_lock(self) -> None:
        for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
            p = self.profile_dir / name
            try:
                if p.exists() or p.is_symlink():
                    p.unlink()
            except Exception:
                pass

    def _kill_profile_chrome(self) -> None:
        prof = str(self.profile_dir)
        ps = (
            "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
            f"Where-Object {{ $_.CommandLine -like '*{prof}*' }} | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force "
            "-ErrorAction SilentlyContinue }"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                timeout=20, capture_output=True,
            )
        except Exception:
            pass
