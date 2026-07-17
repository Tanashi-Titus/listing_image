"""Batch 20 ảnh tuần tự trên ChatGPT web — CHUNG 1 chat, tải từng ảnh đúng thứ tự.

Bền vững:
- RESUME: bỏ qua job đã có ảnh (chạy lại = chạy tiếp).
- Tự KHỞI ĐỘNG LẠI trình duyệt khi nó chết/crash, mở lại chat chung, chạy tiếp.
- Flush RAM định kỳ (reload cùng chat) chống crash bộ nhớ.
- Dừng sạch khi hết lượt Free.
- Lưu tiến độ liên tục ra _results.txt.

Chạy:
    python test_batch20.py [thu_muc_shot]
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
BATCH_DIR = OUTPUT_DIR / "batch20"
SP = PRODUCT_DIR / "sp1.png"
NM = MODEL_DIR / "nm2.png"

BACKGROUNDS = [
    "trắng sạch", "be ấm", "xanh dương pastel", "hồng pastel nhẹ",
    "xám hiện đại", "vàng kem", "xanh mint tươi", "tím lavender",
    "cẩm thạch trắng sang trọng", "nâu gỗ ấm", "gradient cam đào",
    "xanh lá dịu", "hồng ruby đậm", "bạc kim loại", "xanh navy sang trọng",
    "trắng ngà tối giản",
]
THUMB_TEXTS = [
    ("KEM DƯỠNG TRẮNG DA", "GIẢM GIÁ 50%"),
    ("BODY 4 IN 1", "CHÍNH HÃNG"),
    ("MUA 1 TẶNG 1", "SỐ LƯỢNG CÓ HẠN"),
    ("DƯỠNG TRẮNG MỊN MÀNG", "GIÁ CHỈ 199K"),
]
CHAT_HINT = " (Chỉ dựa vào ảnh đính kèm trong tin nhắn NÀY, bỏ qua các ảnh trước đó.)"

LIMIT_HINTS = [
    "limit", "reached", "hết lượt", "giới hạn", "upgrade to", "try again later",
    "you've hit", "maximum", "hạn mức", "come back later", "rate limit",
]


def build_jobs() -> list[dict]:
    jobs = []
    for i, bg in enumerate(BACKGROUNDS, start=1):
        jobs.append({
            "name": f"listing_{i:02d}",
            "images": [SP, NM],
            "prompt": (
                "Đây là ảnh sản phẩm và ảnh người mẫu. Tạo 1 ảnh listing thương mại "
                f"dọc: người mẫu cầm sản phẩm, PHÔNG NỀN {bg.upper()}, ánh sáng "
                "studio, chất lượng cao, chân thực."
            ),
        })
    for i, (top, bottom) in enumerate(THUMB_TEXTS, start=1):
        jobs.append({
            "name": f"thumbnail_{i:02d}",
            "images": [SP],
            "prompt": (
                "Tạo 1 ảnh THUMBNAIL quảng cáo VUÔNG bắt mắt cho sản phẩm này. "
                f"In RÕ chữ tiếng Việt: '{top}' phía trên và '{bottom}' phía dưới. "
                "Chữ phải ĐÚNG CHÍNH TẢ tiếng Việt có dấu, to, rõ, màu nổi bật."
            ),
        })
    return jobs


def log(m: str) -> None:
    print(f">> {m}", flush=True)


def is_crash(e: Exception) -> bool:
    s = str(e).lower()
    return ("crash" in s or "target closed" in s or "has been closed" in s
            or "target page" in s)


def page_has_limit(page) -> bool:
    try:
        txt = page.inner_text("main").lower()
        return any(h in txt for h in LIMIT_HINTS)
    except Exception:
        return False


def run_one(gpt: ChatGPTSession, job: dict) -> str | None:
    """1 job trong chat chung, trả về src ảnh MỚI (baseline) hoặc None."""
    baseline = set(gpt.generated_srcs())
    gpt.upload_images(job["images"])
    gpt.type_prompt(job["prompt"] + CHAT_HINT)
    gpt.send()
    gpt.page.wait_for_timeout(2500)
    return gpt.wait_for_image(timeout_ms=240000, baseline=baseline)


class Runner:
    """Quản lý trình duyệt + chat chung, tự khởi động lại khi chết."""

    def __init__(self) -> None:
        self.br: ChatGPTBrowser | None = None
        self.gpt: ChatGPTSession | None = None
        self.conv_url = ""

    def ensure(self) -> ChatGPTSession:
        if self.br is not None and self.gpt is not None:
            return self.gpt
        log("  → (khởi động trình duyệt)")
        br = ChatGPTBrowser(headless=False)
        br.start()
        br.open_chatgpt()
        if not br.is_logged_in(timeout_ms=15000):
            br.close()
            raise RuntimeError("Chưa đăng nhập — chạy: python cli.py login")
        gpt = ChatGPTSession(br.page)
        # mở lại chat chung cũ nếu đã có, không thì tạo mới
        if self.conv_url:
            gpt.open_conversation(self.conv_url)
        else:
            gpt.new_chat()
        self.br, self.gpt = br, gpt
        return gpt

    def kill(self) -> None:
        try:
            if self.br:
                self.br.close()
        except Exception:
            pass
        self.br = self.gpt = None

    def reload_chat(self) -> None:
        if self.gpt and self.conv_url:
            self.gpt.open_conversation(self.conv_url)


def main() -> None:
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    jobs = build_jobs()

    # RESUME: chỉ chạy job chưa có ảnh
    pending = []
    for idx, job in enumerate(jobs, start=1):
        tag = f"{idx:02d}_{job['name']}"
        if not (BATCH_DIR / f"{tag}.png").exists():
            pending.append((idx, job, tag))
    log(f"Tổng {len(jobs)} job — đã có {len(jobs) - len(pending)}, còn {len(pending)}.")

    runner = Runner()
    results: dict[str, tuple[str, str]] = {}

    def save_report():
        ok = sum(1 for s, _ in results.values() if s == "OK")
        lines = ["========== TỔNG KẾT ==========",
                 f"Thành công (lần này): {ok}/{len(pending)}",
                 f"Tổng ảnh đã có: {len(list(BATCH_DIR.glob('*.png')))}/{len(jobs)}", ""]
        for idx, job in enumerate(jobs, start=1):
            tag = f"{idx:02d}_{job['name']}"
            if (BATCH_DIR / f"{tag}.png").exists():
                st, fn = "OK", f"{tag}.png"
            else:
                st, fn = results.get(tag, ("-", "-"))
            lines.append(f"{tag:28s} | {st:14s} | {fn}")
        (BATCH_DIR / "_results.txt").write_text("\n".join(lines), encoding="utf-8")

    stop = False
    for n, (idx, job, tag) in enumerate(pending, start=1):
        if stop:
            break
        log(f"===== [{n}/{len(pending)}] JOB {idx}: {job['name']} =====")
        done = False
        for attempt in range(1, 4):  # tối đa 3 lần (khởi động lại nếu chết)
            try:
                gpt = runner.ensure()
                src = run_one(gpt, job)
                if not src:
                    if page_has_limit(gpt.page):
                        log(f"✗ HẾT LƯỢT FREE tại job {idx} — dừng.")
                        results[tag] = ("HET_LUOT", "-")
                        stop = True
                        break
                    log(f"  … lần {attempt}: không ra ảnh, thử lại.")
                    continue
                dest = BATCH_DIR / f"{tag}.png"
                gpt.download_image(src, dest)
                if not runner.conv_url:
                    runner.conv_url = gpt.conversation_url()
                size = dest.stat().st_size
                log(f"✓ TẢI: {dest.name} ({size:,} bytes)")
                results[tag] = ("OK", dest.name)
                done = True
                break
            except Exception as e:
                if is_crash(e):
                    log(f"  ⚠ trình duyệt chết (lần {attempt}) — khởi động lại...")
                    runner.kill()
                    time.sleep(2)
                    continue
                log(f"  ✗ lỗi khác: {e!r}")
                results[tag] = (f"LOI:{str(e)[:32]}", "-")
                break
        if not done and tag not in results:
            results[tag] = ("KHONG_CO_ANH", "-")
        save_report()

        # flush RAM mỗi 4 ảnh (vẫn cùng chat)
        if done and n % 4 == 0 and n < len(pending):
            log("  ↻ reload chat để giải phóng RAM...")
            try:
                runner.reload_chat()
            except Exception:
                runner.kill()
        if done:
            time.sleep(5)

    save_report()
    log("HOÀN TẤT.")
    runner.kill()


if __name__ == "__main__":
    main()
