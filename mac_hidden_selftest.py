"""
mac_hidden_selftest.py — Kiểm CHẾ ĐỘ CHẠY NGẦM (hidden) trên máy Mac THẬT
(runner macOS của GitHub Actions). Không cần GUI, không cần máy Mac riêng.

Kiểm đúng 2 thứ quyết định "chạy ngầm có dùng được không" trên Mac:
  1. Cửa sổ Chrome có THẬT SỰ ra khỏi tầm mắt không (ngoài mọi màn hình, hoặc
     thu nhỏ xuống Dock). Bản cũ chỉ đặt toạ độ âm — macOS kéo cửa sổ về lại
     màn hình nên chế độ ẩn VÔ TÁC DỤNG.
  2. Khi đã ẩn, trang có còn CHẠY HẾT TỐC ĐỘ không. Chrome mặc định "ngủ đông"
     tab bị che/thu nhỏ (timer 1 lần/phút) → ChatGPT sẽ đứng giữa chừng. Các cờ
     trong ANTI_THROTTLE_ARGS phải chặn được việc đó.

Chạy:  python mac_hidden_selftest.py   → exit != 0 nếu hỏng (CI báo đỏ).
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:                       # console Windows mặc định cp1252 → không in tiếng Việt
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from core.aio_browser import (  # noqa: E402
    AioBrowser, IS_MAC, _virtual_right_edge, _offscreen_xy,
)

FAILS = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("✅ " if ok else "❌ ") + name + (f"  → {detail}" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


async def main() -> None:
    print("== macOS hidden-mode self-test ==")
    print("platform:", sys.platform)
    print("mép phải vùng màn hình:", _virtual_right_edge())
    print("toạ độ ẩn dự kiến     :", _offscreen_xy())

    profile = Path(tempfile.mkdtemp(prefix="tnt_hidden_"))
    br = AioBrowser(profile_dir=profile, hidden=True)
    await br.start()
    try:
        page = await br.first_page()
        await page.goto("about:blank")
        await br.apply_hidden()

        # --- 1) cửa sổ có ra khỏi tầm mắt không? --- #
        cdp = await br.context.new_cdp_session(page)
        wid = (await cdp.send("Browser.getWindowForTarget"))["windowId"]
        bounds = (await cdp.send("Browser.getWindowBounds",
                                 {"windowId": wid}))["bounds"]
        print("bounds cửa sổ:", bounds)
        offscreen = await br._is_offscreen(cdp, wid)
        check("cửa sổ nằm ngoài tầm mắt (offscreen hoặc minimized)",
              offscreen, str(bounds))

        # --- 2) trang còn chạy hết tốc độ khi đã ẩn không? --- #
        # Đếm nhịp setTimeout trong 3 giây. Tab bị Chrome "ngủ đông" chỉ được
        # ~1 nhịp/phút → đếm sẽ gần 0.
        ticks = await page.evaluate(
            """() => new Promise(res => {
                let n = 0;
                const t0 = Date.now();
                (function loop() {
                    if (Date.now() - t0 >= 3000) return res(n);
                    n++;
                    setTimeout(loop, 50);
                })();
            })"""
        )
        print("số nhịp setTimeout trong 3s:", ticks)
        # 3s / 50ms ≈ 60 nhịp nếu chạy bình thường; lấy mốc 25 cho rộng rãi.
        check("timer KHÔNG bị Chrome bóp khi cửa sổ ẩn", ticks >= 25,
              f"chỉ {ticks} nhịp — thiếu cờ chống throttle?")

        # --- 3) DOM vẫn cập nhật & đọc được (thứ code này dựa vào) --- #
        got = await page.evaluate(
            """() => new Promise(res => {
                setTimeout(() => {
                    const d = document.createElement('div');
                    d.id = 'tnt-probe';
                    d.textContent = 'xin chao';
                    document.body.appendChild(d);
                    setTimeout(() => res(
                        (document.getElementById('tnt-probe') || {}).innerText || ''
                    ), 200);
                }, 200);
            })"""
        )
        check("DOM vẫn ghi/đọc được khi ẩn", got.strip() == "xin chao", repr(got))

        # --- 4) mở thêm tab (tạo ảnh song song) vẫn giữ trạng thái ẩn --- #
        page2 = await br.new_page()
        await page2.goto("about:blank")
        cdp2 = await br.context.new_cdp_session(page2)
        wid2 = (await cdp2.send("Browser.getWindowForTarget"))["windowId"]
        still = await br._is_offscreen(cdp2, wid2)
        check("mở thêm tab vẫn ẩn", still,
              str((await cdp2.send("Browser.getWindowBounds",
                                   {"windowId": wid2}))["bounds"]))
    finally:
        await br.close()

    if not IS_MAC:
        print("\nℹ️  Không phải macOS — bài test vẫn có ý nghĩa hồi quy cho Windows.")
    print(f"\n==> {'HỎNG: ' + ', '.join(FAILS) if FAILS else 'TẤT CẢ ĐỀU ĐẠT'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    asyncio.run(main())
