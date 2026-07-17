"""Test khâu analyze: attributes + prompts + copy + shopee text."""
from __future__ import annotations

import asyncio
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from config import PRODUCT_DIR
from core.aio_browser import AioBrowser
from core.aio_chatgpt import AioSession
from core.analyzer import analyze


async def main() -> None:
    br = AioBrowser(headless=False)
    await br.start()
    page = await br.first_page()
    await br.open_chatgpt(page)
    if not await br.is_logged_in(page, 15000):
        print(">> chua dang nhap"); await br.close(); return
    s = AioSession(page)
    types = ["thumbnail", "detail_info", "in_use"]
    print(">> analyze...", flush=True)
    res = await analyze(s, PRODUCT_DIR / "sp1.png", types, language="vi",
                        product_info="Kem dưỡng trắng da body 4in1, có SPF50, collagen, arbutin")
    print(">> ATTRIBUTES:", flush=True)
    print(json.dumps(res["attributes"], ensure_ascii=False, indent=2)[:800], flush=True)
    print(f">> PROMPTS: {len(res['prompts'])} cái", flush=True)
    for p in res["prompts"]:
        print(f"  [{p['type']}] {p['prompt'][:110]}...", flush=True)
    print(">> COPY_PACK keys:", list(res["copy_pack"].keys()), flush=True)
    print(">> SHOPEE title:", str(res["shopee_text"].get("title"))[:100], flush=True)
    await br.close()
    print(">> DONE", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
