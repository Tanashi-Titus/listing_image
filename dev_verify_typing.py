"""Xác minh prompt gõ vào ô soạn KHÔNG bị xáo trộn (không gửi → không tốn ảnh)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from config import profile_path
from core.aio_browser import AioBrowser
from core.aio_chatgpt import AioSession, SEL_COMPOSER
from core.generator import _build_final_prompt

SHOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

SAMPLE = _build_final_prompt(
    "Sản phẩm là chủ thể chính đặt ở góc nghiêng khoảng 15 độ. Chụp macro bằng "
    "ống kính 100mm, khẩu độ f/5.6, bố cục cân đối nhiều khoảng trắng. Ánh sáng "
    "studio hai bên tạo chiều sâu. Hậu cảnh marble sáng kết hợp nền gỗ mờ dần. "
    "Bên cạnh có thẻ thông tin thiết kế hiện đại. Typography tiếng Việt rất lớn, "
    "đậm, sạch, tiêu đề chiếm 20% diện tích.",
    [Path("sp1.png")], False, False,
)


async def main() -> None:
    br = AioBrowser(profile_dir=profile_path("acc2"))
    await br.start()
    try:
        page = await br.first_page()
        await br.open_chatgpt(page)
        s = AioSession(page)
        await s.new_chat()
        await s.type_prompt(SAMPLE)
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(SHOT / "typing_check.png"))
        got = await page.evaluate(
            f"() => document.querySelector('{SEL_COMPOSER}').innerText"
        )
        intended = " ".join(SAMPLE.split())
        got_clean = " ".join(got.split())
        print(">> KHỚP:", got_clean == intended, flush=True)
        if got_clean != intended:
            print(">> intended[:80]:", intended[:80], flush=True)
            print(">> got[:80]     :", got_clean[:80], flush=True)
            print(">> intended[-60:]:", intended[-60:], flush=True)
            print(">> got[-60:]     :", got_clean[-60:], flush=True)
        else:
            print(">> Prompt nhập CHÍNH XÁC, không xáo trộn.", flush=True)
    finally:
        await br.close()


if __name__ == "__main__":
    asyncio.run(main())
