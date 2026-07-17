"""Test tạo 1 ảnh listing end-to-end (dev).

Chạy:
    python test_one.py <thu_muc_screenshot>
"""
from __future__ import annotations

import sys
from pathlib import Path

# Console Windows mặc định cp1252 -> ép UTF-8 để in tiếng Việt không lỗi.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from config import PRODUCT_DIR, MODEL_DIR, OUTPUT_DIR
from core.browser import ChatGPTBrowser
from core.chatgpt import ChatGPTSession

SHOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

PROMPT = (
    "Đây là 2 ảnh: ảnh 1 là sản phẩm, ảnh 2 là người mẫu. "
    "Hãy tạo 1 ảnh listing thương mại: cho người mẫu mặc/cầm sản phẩm này, "
    "bố cục đẹp, ánh sáng studio, nền sạch, chất lượng cao."
)


def log(msg: str) -> None:
    print(f">> {msg}", flush=True)


def main() -> None:
    products = sorted(PRODUCT_DIR.glob("*.png")) + sorted(PRODUCT_DIR.glob("*.jpg"))
    models = sorted(MODEL_DIR.glob("*.png")) + sorted(MODEL_DIR.glob("*.jpg"))
    if not products or not models:
        log(f"Thiếu ảnh. san_pham={products} nguoi_mau={models}")
        return
    imgs = [products[0], models[0]]
    log(f"Ảnh dùng: {[p.name for p in imgs]}")

    br = ChatGPTBrowser(headless=False)
    br.start()
    br.open_chatgpt()
    if not br.is_logged_in(timeout_ms=15000):
        log("Chưa đăng nhập — chạy: python cli.py login")
        br.close()
        return

    gpt = ChatGPTSession(br.page)

    try:
        log("Mở chat mới...")
        gpt.new_chat()
        br.page.screenshot(path=str(SHOT / "s1_newchat.png"))

        log("Upload ảnh...")
        n = gpt.upload_images(imgs)
        log(f"Số thumbnail thấy: {n}")
        br.page.screenshot(path=str(SHOT / "s2_uploaded.png"))

        log("Gõ prompt...")
        gpt.type_prompt(PROMPT)
        br.page.screenshot(path=str(SHOT / "s3_typed.png"))

        log("Gửi...")
        gpt.send()
        br.page.wait_for_timeout(3000)
        br.page.screenshot(path=str(SHOT / "s4_sent.png"))

        log("Chờ ảnh (tối đa 4 phút)...")
        src = gpt.wait_for_image(timeout_ms=240000)
        br.page.screenshot(path=str(SHOT / "s5_done.png"))
        log(f"Ảnh src: {str(src)[:80] if src else None}")

        if src:
            dest = OUTPUT_DIR / "test" / "v1.png"
            gpt.download_image(src, dest)
            log(f"✓ ĐÃ TẢI: {dest}")
        else:
            log("✗ Không thấy ảnh — xem screenshot s4/s5 để chẩn đoán.")

        log(f"URL chat: {gpt.conversation_url()}")
    except Exception as e:
        log(f"LỖI: {e!r}")
        try:
            br.page.screenshot(path=str(SHOT / "s_error.png"))
        except Exception:
            pass
    finally:
        br.page.wait_for_timeout(1500)
        br.close()


if __name__ == "__main__":
    main()
