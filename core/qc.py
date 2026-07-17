"""Khâu QC ảnh qua ChatGPT web (vision) — 'lenient', KHÔNG chặn (chỉ cảnh báo).

Tốn thêm 1 message/ảnh nên mặc định TẮT (DEFAULT_QC=False) để chạy nhanh.
"""
from __future__ import annotations

from pathlib import Path

from core.aio_chatgpt import AioSession
from core.jsonutil import parse_json


async def qc_image(
    session: AioSession,
    image_path: Path,
    attributes: dict,
    timeout_ms: int = 90000,
) -> dict:
    """Kiểm ảnh có đúng sản phẩm / có chữ lỗi không. Nghi ngờ thì PASS."""
    try:
        await session.new_chat()
        await session.upload_images([Path(image_path)])
        prompt = (
            "Bạn là QC ảnh quảng cáo, đánh giá KHOAN DUNG (nghi ngờ thì cho PASS). "
            f"Sản phẩm mong đợi: {attributes.get('short_descriptor', '')} "
            f"(nhãn: {attributes.get('exact_label_string', '')}). "
            "Nhìn ảnh và CHỈ trả JSON: "
            '{"product_match":true,"label_ok":true,"no_placeholder_text":true,'
            '"sharp":true,"issues":[]}'
        )
        text = await session.ask_text(prompt, timeout_ms=timeout_ms)
        return parse_json(text)
    except Exception as e:
        # QC lỗi → coi như PASS (không chặn)
        return {
            "product_match": True, "label_ok": True, "no_placeholder_text": True,
            "sharp": True, "issues": [f"qc_skipped: {e}"],
        }
