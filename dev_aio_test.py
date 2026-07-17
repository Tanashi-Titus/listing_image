"""Test nhanh async core: login + hỏi 1 câu text."""
from __future__ import annotations

import asyncio
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from core.aio_browser import AioBrowser
from core.aio_chatgpt import AioSession


async def main() -> None:
    br = AioBrowser(headless=False)
    await br.start()
    page = await br.first_page()
    await br.open_chatgpt(page)
    logged = await br.is_logged_in(page, timeout_ms=15000)
    print(">> logged_in:", logged, flush=True)
    if not logged:
        await br.close()
        return
    s = AioSession(page)
    await s.new_chat()
    ans = await s.ask_text("Trả lời đúng 2 từ, không thêm gì: XIN CHÀO", timeout_ms=60000)
    print(">> answer:", repr(ans[:120]), flush=True)
    await br.close()
    print(">> DONE", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
