"""Dump RAW output của generate_prompts_and_text để xem model trả gì."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from config import PROMPT_TYPE_KEYS, profile_path
from core.aio_browser import AioBrowser
from core.aio_chatgpt import AioSession
from core.analyzer import extract_attributes, generate_prompts_and_text

PROFILE = sys.argv[1] if len(sys.argv) > 1 else "acc3"
MODE = sys.argv[2] if len(sys.argv) > 2 else "hidden"
OUT = sys.argv[3] if len(sys.argv) > 3 else "raw_prompts.json"


async def main() -> None:
    br = AioBrowser(profile_dir=profile_path(PROFILE),
                    hidden=(MODE == "hidden"), headless=(MODE == "headless"))
    await br.start()
    page = await br.first_page()
    await br.open_chatgpt(page)
    if not await br.is_logged_in(page, 15000):
        print("chua dang nhap"); await br.close(); return
    s = AioSession(page)
    attrs = await extract_attributes(s, "data/nguoi_mau/maysay.png",
                                     "Panasoni 3500W hair dryer")
    print(">> attrs keys:", list(attrs.keys()), flush=True)
    data = await generate_prompts_and_text(
        s, attrs, list(PROMPT_TYPE_KEYS), language="en", shop="TNT Store",
    )
    print(">> data type:", type(data).__name__, flush=True)
    print(">> data keys:", list(data.keys()) if isinstance(data, dict) else "N/A", flush=True)
    raw_prompts = data.get("prompts") if isinstance(data, dict) else None
    print(">> prompts type:", type(raw_prompts).__name__, flush=True)
    if isinstance(raw_prompts, list):
        print(">> so prompt:", len(raw_prompts), flush=True)
        print(">> types:", [p.get("type") if isinstance(p, dict) else type(p).__name__
                            for p in raw_prompts], flush=True)
    Path(OUT).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(">> da ghi raw ra:", OUT, flush=True)
    await br.close()


if __name__ == "__main__":
    asyncio.run(main())
