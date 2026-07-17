"""Test batch (GĐ3): chạy 3 job lần lượt, tải ảnh về theo đúng thứ tự.

Job 3 test chữ tiếng Việt render trên ảnh thumbnail.
Có xử lý: hết lượt Free -> dừng, ghi lý do.

Chạy:
    python test_batch.py [thu_muc_shot]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from config import PRODUCT_DIR, MODEL_DIR, OUTPUT_DIR
from core.browser import ChatGPTBrowser
from core.chatgpt import ChatGPTSession

SHOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
BATCH_DIR = OUTPUT_DIR / "batch"

SP = PRODUCT_DIR / "sp1.png"
NM = MODEL_DIR / "nm2.png"

# 3 job khác nhau rõ rệt để kiểm tra thứ tự tải
JOBS = [
    {
        "name": "listing_nen_trang",
        "images": [SP, NM],
        "prompt": (
            "Đây là ảnh sản phẩm và ảnh người mẫu. Tạo 1 ảnh listing thương mại "
            "dọc: người mẫu cầm sản phẩm, PHÔNG NỀN TRẮNG SẠCH, ánh sáng studio, "
            "chất lượng cao."
        ),
    },
    {
        "name": "listing_nen_xanh",
        "images": [SP, NM],
        "prompt": (
            "Đây là ảnh sản phẩm và ảnh người mẫu. Tạo 1 ảnh listing thương mại "
            "dọc: người mẫu cầm sản phẩm, PHÔNG NỀN XANH DƯƠNG PASTEL nổi bật, "
            "ánh sáng mềm, chất lượng cao."
        ),
    },
    {
        "name": "thumbnail_chu_tiengviet",
        "images": [SP],
        "prompt": (
            "Tạo 1 ảnh THUMBNAIL quảng cáo VUÔNG cho sản phẩm này. "
            "Trên ảnh hãy in RÕ dòng chữ tiếng Việt lớn: "
            "'KEM DƯỠNG TRẮNG DA' ở trên và 'GIẢM GIÁ 50%' ở dưới. "
            "Chữ phải đúng chính tả tiếng Việt có dấu, màu nổi bật, dễ đọc."
        ),
    },
]

# dấu hiệu hết lượt Free
LIMIT_HINTS = [
    "limit", "reached", "hết lượt", "giới hạn", "upgrade to", "try again later",
    "you've hit", "maximum", "hạn mức",
]


def log(m: str) -> None:
    print(f">> {m}", flush=True)


def page_has_limit(page) -> bool:
    try:
        txt = page.inner_text("main").lower()
        return any(h in txt for h in LIMIT_HINTS)
    except Exception:
        return False


def main() -> None:
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    br = ChatGPTBrowser(headless=False)
    br.start()
    br.open_chatgpt()
    if not br.is_logged_in(timeout_ms=15000):
        log("Chưa đăng nhập — chạy: python cli.py login")
        br.close()
        return

    gpt = ChatGPTSession(br.page)
    results = []

    for idx, job in enumerate(JOBS, start=1):
        tag = f"{idx:02d}_{job['name']}"
        log(f"===== JOB {idx}/{len(JOBS)}: {job['name']} =====")
        try:
            gpt.new_chat()
            log(f"Upload {[Path(p).name for p in job['images']]}")
            gpt.upload_images(job["images"])
            gpt.type_prompt(job["prompt"])
            gpt.send()
            br.page.wait_for_timeout(2500)
            br.page.screenshot(path=str(SHOT / f"b{idx}_sent.png"))

            src = gpt.wait_for_image(timeout_ms=240000)
            if not src:
                if page_has_limit(br.page):
                    log("✗ HẾT LƯỢT FREE (limit) — dừng batch.")
                    results.append((tag, "HET_LUOT", None, gpt.conversation_url()))
                    br.page.screenshot(path=str(SHOT / f"b{idx}_limit.png"))
                    break
                log("✗ Không thấy ảnh (không rõ lý do).")
                results.append((tag, "KHONG_CO_ANH", None, gpt.conversation_url()))
                br.page.screenshot(path=str(SHOT / f"b{idx}_noimg.png"))
                continue

            dest = BATCH_DIR / f"{tag}.png"
            gpt.download_image(src, dest)
            size = Path(dest).stat().st_size
            log(f"✓ TẢI: {dest.name} ({size} bytes)")
            results.append((tag, "OK", str(dest), gpt.conversation_url()))

            # nghỉ giữa các job (giống người, đỡ bị chặn)
            if idx < len(JOBS):
                time.sleep(4)
        except Exception as e:
            log(f"LỖI job {idx}: {e!r}")
            results.append((tag, f"LOI:{e!r}"[:60], None, ""))
            try:
                br.page.screenshot(path=str(SHOT / f"b{idx}_error.png"))
            except Exception:
                pass

    log("")
    log("========== TỔNG KẾT ==========")
    for tag, status, dest, url in results:
        log(f"{tag:32s} | {status:14s} | {Path(dest).name if dest else '-'}")

    br.page.wait_for_timeout(1500)
    br.close()


if __name__ == "__main__":
    main()
