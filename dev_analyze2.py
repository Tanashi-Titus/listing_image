"""Test analyze theo logic docx: 9 prompt EN + theme + SEO (không tốn quota ảnh)."""
from __future__ import annotations

import asyncio
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from config import PROMPT_TYPE_KEYS, profile_path
from core.aio_browser import AioBrowser
from core.aio_chatgpt import AioSession
from core.analyzer import analyze

PROFILE = sys.argv[1] if len(sys.argv) > 1 else "acc2"
MODE = sys.argv[2] if len(sys.argv) > 2 else "normal"  # normal|headless|hidden


async def main() -> None:
    print(f">> mode={MODE}", flush=True)
    br = AioBrowser(
        profile_dir=profile_path(PROFILE),
        headless=(MODE == "headless"),
        hidden=(MODE == "hidden"),
    )
    await br.start()
    page = await br.first_page()
    await br.open_chatgpt(page)
    if not await br.is_logged_in(page, 15000):
        print(">> chua dang nhap"); await br.close(); return
    s = AioSession(page)
    print(">> analyze (9 loai, EN, shop TNT Store)...", flush=True)
    res = await analyze(
        s, "data/nguoi_mau/maysay.png", list(PROMPT_TYPE_KEYS), language="en",
        product_info="Panasoni Salon Compact 3500W professional hair dryer, long power cord, detachable nozzle",
        shop="TNT Store", market="Philippines",
    )
    print(">> THEME:", res.get("theme"), flush=True)
    print(f">> PROMPTS: {len(res['prompts'])}", flush=True)
    for p in res["prompts"]:
        print(f"  [{p['type']}] {p['prompt'][:130]}...", flush=True)
    print("\n>> SEO:", flush=True)
    print(json.dumps(res.get("seo", {}), ensure_ascii=False, indent=2), flush=True)
    await br.close()
    print(">> DONE", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
