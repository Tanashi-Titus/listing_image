"""Integration test — luồng THẬT qua ChatGPT web (cần đã đăng nhập).

Mặc định chỉ test khâu KHÔNG tốn lượt ảnh (login + analyze).
Bật test tạo ảnh (tốn quota Free) bằng biến môi trường:
    LISTING_TEST_IMAGES=1

Chọn profile:
    LISTING_TEST_PROFILE=acc2   (mặc định: default)

Chạy:
    python tests/test_integration.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from config import PRODUCT_DIR, MODEL_DIR, profile_path
from core.aio_browser import AioBrowser
from core.aio_chatgpt import AioSession
from core.analyzer import analyze
from core.generator import generate_one
from core.pipeline import run_pipeline

PROFILE = os.environ.get("LISTING_TEST_PROFILE") or None
TEST_IMAGES = os.environ.get("LISTING_TEST_IMAGES") == "1"
PRODUCT = PRODUCT_DIR / "sp1.png"
PERSON = MODEL_DIR / "nm2.png"

_results = []


def check(name: str, cond: bool, info: str = "") -> None:
    _results.append((name, cond, info))
    print(f"  {'PASS' if cond else 'FAIL'} {name}" + (f" — {info}" if info else ""),
          flush=True)


async def t_login_and_analyze() -> None:
    br = AioBrowser(profile_dir=profile_path(PROFILE))
    await br.start()
    try:
        page = await br.first_page()
        await br.open_chatgpt(page)
        logged = await br.is_logged_in(page)
        check("login", logged, f"profile={PROFILE or 'default'}")
        if not logged:
            return
        s = AioSession(page)
        res = await analyze(s, PRODUCT, ["thumbnail", "detail_info"], "vi",
                            product_info="Kem dưỡng trắng body")
        check("analyze_attributes", bool(res["attributes"].get("brand")),
              f"brand={res['attributes'].get('brand')}")
        check("analyze_prompts_count", len(res["prompts"]) == 2,
              f"n={len(res['prompts'])}")
        check("analyze_prompt_nonempty",
              all(p["prompt"] for p in res["prompts"]))
    finally:
        await br.close()


async def t_typing_integrity() -> None:
    """Kiểm prompt nhập vào ô soạn KHÔNG bị xáo trộn (không gửi → free)."""
    from core.aio_chatgpt import SEL_COMPOSER
    from core.generator import _build_final_prompt
    sample = _build_final_prompt(
        "Sản phẩm chính diện nghiêng 15 độ, macro 100mm f/5.6, ánh sáng studio "
        "hai bên, nền marble sáng, thẻ thông tin bên cạnh, typography tiếng Việt "
        "rất lớn đậm sạch chiếm 20% diện tích ảnh.",
        [Path("sp.png"), Path("per.png")], True, False,
    )
    br = AioBrowser(profile_dir=profile_path(PROFILE))
    await br.start()
    try:
        page = await br.first_page()
        await br.open_chatgpt(page)
        if not await br.is_logged_in(page):
            check("typing_integrity", False, "chưa đăng nhập")
            return
        s = AioSession(page)
        await s.new_chat()
        await s.type_prompt(sample)
        await page.wait_for_timeout(500)
        got = await page.evaluate(
            f"() => document.querySelector('{SEL_COMPOSER}').innerText"
        )
        check("typing_integrity",
              " ".join(got.split()) == " ".join(sample.split()),
              "prompt khớp nguyên vẹn")
    finally:
        await br.close()


async def t_generate_one() -> None:
    br = AioBrowser(profile_dir=profile_path(PROFILE))
    await br.start()
    try:
        page = await br.first_page()
        await br.open_chatgpt(page)
        if not await br.is_logged_in(page):
            check("gen_one", False, "chưa đăng nhập")
            return
        s = AioSession(page)
        prompt_obj = {
            "type": "thumbnail", "label": "Ảnh bìa",
            "prompt": "Ảnh bìa sản phẩm, nền trắng sạch, ánh sáng studio, chữ lớn 'TEST'.",
            "content": "",
        }
        out = Path(__file__).resolve().parent.parent / "ket_qua" / "_test" / "one.png"
        res = await generate_one(s, prompt_obj, PRODUCT, PERSON, None, dest=out)
        check("gen_one", res["status"] == "success" and Path(out).exists(),
              f"status={res['status']}")
    finally:
        await br.close()


async def t_pipeline_small() -> None:
    out = await run_pipeline(
        product=PRODUCT, person=PERSON,
        types=["thumbnail", "detail_info"], quantity=2, concurrency=2,
        product_info="Kem dưỡng trắng body 4in1", profile_dir=profile_path(PROFILE),
    )
    check("pipeline_ok_count", out["ok_count"] >= 1, f"{out['ok_count']}/{out['total']}")
    check("pipeline_zip", Path(out["zip"]).exists())
    check("pipeline_prompts_txt", (Path(out["dir"]) / "prompts.txt").exists())
    check("pipeline_listing_txt", (Path(out["dir"]) / "listing_text.txt").exists())


async def main() -> None:
    print("== login + analyze ==", flush=True)
    await t_login_and_analyze()
    print("== typing integrity (free) ==", flush=True)
    await t_typing_integrity()
    if TEST_IMAGES:
        print("== generate one (tốn 1 ảnh) ==", flush=True)
        await t_generate_one()
        print("== pipeline nhỏ (tốn 2 ảnh) ==", flush=True)
        await t_pipeline_small()
    else:
        print("(bỏ qua test tạo ảnh — đặt LISTING_TEST_IMAGES=1 để bật)", flush=True)

    passed = sum(1 for _, c, _ in _results if c)
    total = len(_results)
    print(f"\n==> {passed}/{total} PASS", flush=True)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
