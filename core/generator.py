"""Khâu TẠO ẢNH qua ChatGPT web (1 ảnh / 1 tab / 1 chat mới).

Web cho upload nhiều ảnh cùng lúc → KHÔNG cần ghép PIL như bản API (edits).
Ta upload thẳng: sản phẩm (+ người / + cảnh tùy loại). Model giữ sản phẩm
tốt hơn khi thấy ảnh gốc rõ ràng.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PIL import Image

from core.aio_chatgpt import AioSession, StopRequested
from config import USE_PERSON_TYPES, USE_SCENE_TYPES, TARGET_SIZE


def overlay_logo(image_path: Path, logo_path: Path,
                 ratio: float = 0.17, margin: float = 0.035) -> None:
    """Dán LOGO THẬT (ảnh) vào góc trên-phải — logo chính xác 100%, không do AI vẽ."""
    try:
        img = Image.open(image_path).convert("RGBA")
        W, H = img.size
        logo = Image.open(logo_path).convert("RGBA")
        lw = max(1, int(W * ratio))
        lh = max(1, int(logo.height * lw / logo.width))
        logo = logo.resize((lw, lh), Image.LANCZOS)
        m = int(W * margin)
        img.alpha_composite(logo, (W - lw - m, m))
        img.convert("RGB").save(image_path)
    except Exception:
        pass


def to_square(path: Path, size: int = TARGET_SIZE) -> None:
    """Ép ảnh về VUÔNG size×size. Nếu chưa vuông thì đệm viền bằng màu mép ảnh."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    if w != h:
        side = max(w, h)
        px = img.load()
        corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
        avg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
        canvas = Image.new("RGB", (side, side), avg)
        canvas.paste(img, ((side - w) // 2, (side - h) // 2))
        img = canvas
    if img.size != (size, size):
        img = img.resize((size, size), Image.LANCZOS)
    img.save(path)


def select_refs(
    p_type: str,
    product: Path,
    person: Optional[Path] = None,
    scene: Optional[Path] = None,
) -> List[Path]:
    """Chọn ảnh tham chiếu upload theo loại ảnh (giống USE_*_TYPES của MD)."""
    refs: List[Path] = [Path(product)]
    if p_type in USE_PERSON_TYPES and person:
        refs.append(Path(person))
    if p_type in USE_SCENE_TYPES and scene:
        refs.append(Path(scene))
    return refs


# Chỉ thị CHÂN THỰC — chống vẻ AI, áp cho mọi ảnh.
REALISM = (
    "Ảnh CHỤP THẬT chuyên nghiệp bằng máy DSLR full-frame (ống kính 50mm f/4), "
    "phong cách nhiếp ảnh thương mại chân thực như ảnh studio thật, KHÔNG phải "
    "AI/3D render/CGI. Bề mặt vật có chất liệu & phản chiếu tự nhiên đúng vật lý; "
    "nếu có người thì DA có kết cấu và lỗ chân lông, KHÔNG làm mịn/nhựa hóa, tóc "
    "có sợi bay tự nhiên; ánh sáng vật lý đúng, bóng đổ mềm nhất quán một nguồn "
    "sáng; bokeh quang học và độ sâu trường ảnh thật; màu TRUNG THỰC không rực "
    "giả, cân bằng trắng tự nhiên; hạt film rất nhẹ. Tránh đối xứng máy móc, "
    "tránh bóng nhựa/CGI, tránh vẻ hoàn hảo giả tạo, tránh over-sharpen/HDR quá."
)
# Chỉ thị ĐÚNG LOGIC — chống lỗi AI (méo, thừa ngón, chữ vô nghĩa, vật lơ lửng...).
LOGIC = (
    "PHẢI ĐÚNG LOGIC & GIẢI PHẪU, KHÔNG lỗi kiểu AI: sản phẩm hiển thị NGUYÊN "
    "VẸN đúng hình dạng thật, KHÔNG méo mó/biến dạng/tan chảy, KHÔNG tự nhân đôi "
    "hay lặp sản phẩm ngoài ý muốn, KHÔNG thừa/thiếu bộ phận. Nếu có bàn tay: "
    "ĐÚNG 5 ngón, cầm nắm tự nhiên đúng cách dùng thực tế, không dính/thừa/thiếu "
    "ngón, khớp và tỉ lệ tay đúng. Vật đặt trên bề mặt phải có ĐIỂM TỰA thật, "
    "KHÔNG lơ lửng; bóng đổ và phản chiếu khớp đúng vị trí vật và nguồn sáng. "
    "Mọi CHỮ trong ảnh phải là từ CÓ NGHĨA, đúng chính tả, KHÔNG chữ méo/nhòe/vô "
    "nghĩa, không lặp chữ lỗi. Tỉ lệ, phối cảnh, số lượng vật thể hợp lý thực tế."
)
_MODEST = "Modest, fully appropriate commercial advertising photography."


def _build_final_prompt(prompt: str, refs: List[Path], has_person: bool,
                        has_scene: bool, notable_details=None,
                        theme: str = "", shop: str = "", logo_img: bool = False) -> str:
    """Ghép prompt cuối: nội dung + giữ nguyên sản phẩm/người + CHÂN THỰC + an toàn."""
    notes = []
    if theme:
        notes.append(f"Đồng bộ theme thiết kế chung cả bộ: {theme}.")
    if logo_img:
        # có ảnh logo thật → chừa chỗ, KHÔNG để AI tự vẽ logo (dán logo thật sau)
        notes.append(
            "CHỪA GÓC TRÊN-PHẢI trống sạch (~18% chiều rộng) để dán LOGO SHOP thật "
            "vào sau; TUYỆT ĐỐI KHÔNG tự vẽ logo/chữ thương hiệu shop nào."
        )
    elif shop:
        notes.append(f"Thêm logo shop '{shop}' ở góc, nhất quán.")
    if len(refs) == 1:
        notes.append(
            "Ảnh đính kèm là SẢN PHẨM: giữ NGUYÊN thiết kế, nhãn, chữ, màu sắc, "
            "tỉ lệ y hệt, không đổi bao bì. Hiển thị ĐẦY ĐỦ sản phẩm gồm MỌI bộ "
            "phận (dây điện/cáp, nút bấm, đầu phụ kiện, khe gió...), không cắt "
            "xén, không bỏ sót chi tiết."
        )
    else:
        parts = [
            "Ảnh 1 là SẢN PHẨM (giữ NGUYÊN thiết kế, nhãn, chữ, màu sắc; hiển thị "
            "ĐẦY ĐỦ mọi bộ phận gồm dây điện, nút, đầu phụ kiện — không bỏ sót)."
        ]
        i = 2
        if has_person:
            parts.append(
                f"Ảnh {i} là NGƯỜI MẪU: BẮT BUỘC đưa CHÍNH người mẫu này vào ảnh "
                "(ảnh PHẢI có người mẫu), giữ ĐÚNG gương mặt, kiểu tóc và tông da; "
                "người mẫu ĐANG CẦM/DÙNG sản phẩm đúng cách thực tế, tương tác tự "
                "nhiên (tư thế & tay cầm đúng, ánh mắt và biểu cảm phù hợp); bố cục "
                "có CẢ người mẫu VÀ sản phẩm, sản phẩm vẫn rõ nét, nổi bật, KHÔNG bị "
                "che khuất; giữ nguyên thiết kế sản phẩm."
            )
            i += 1
        if has_scene:
            parts.append(
                f"Ảnh {i} là BỐI CẢNH: dùng CHÍNH bối cảnh này làm khung cảnh nền, "
                "đặt sản phẩm/người mẫu hoà hợp tự nhiên vào không gian đó."
            )
        notes.append(" ".join(parts))
        if has_person and not has_scene:
            notes.append(
                "TỰ DỰNG bối cảnh/nền lifestyle phù hợp, sạch và đúng theme cho người "
                "mẫu (vd phòng tắm/bàn trang điểm/không gian studio sáng hợp ngữ cảnh "
                "sản phẩm), có chiều sâu thật; ánh sáng ăn khớp giữa người mẫu và sản "
                "phẩm để ảnh liền mạch, không giống ghép cắt dán."
            )

    if notable_details:
        dl = ", ".join(str(d) for d in notable_details if d)
        if dl:
            notes.append(f"Chú ý tái hiện đúng các chi tiết: {dl}.")

    notes.append(
        "HƯỚNG SẢN PHẨM PHẢI ĐÚNG THỰC TẾ: KHÔNG lật ngược, KHÔNG xoay sai hướng, "
        "KHÔNG cầm ngược. Thiết bị cầm tay: phần tay cầm/handle hướng xuống dưới, "
        "đầu hoạt động (đầu thổi gió / vòi xịt / miệng ra / đầu bàn chải / lưỡi...) "
        "hướng đúng như thiết kế gốc và đúng công năng sử dụng."
    )
    if has_person:
        notes.append(
            "NGƯỜI MẪU DÙNG SẢN PHẨM PHẢI CHÂN THỰC & ĐÚNG CÔNG NĂNG: đầu hoạt động "
            "của sản phẩm PHẢI HƯỚNG VÀO đúng bộ phận/đối tượng đang được tác động — "
            "vd MÁY SẤY thì MIỆNG THỔI GIÓ chĩa THẲNG VÀO tóc để sấy (KHÔNG chĩa ra "
            "xa, KHÔNG hướng ngược, KHÔNG cầm lộn đầu); lược/bàn chải/mỹ phẩm/dụng cụ "
            "thì áp đúng vùng đang dùng. Tay cầm đúng cách cầm thật, khoảng cách và "
            "góc thao tác hợp lý, động tác tự nhiên như đang dùng thật; luồng gió/tia "
            "xịt/hướng tác động phải NHẤT QUÁN với động tác và vị trí của người mẫu. "
            "Tuyệt đối không để sản phẩm lơ lửng sai tư thế hay dùng sai chức năng."
        )
    notes.append(
        "KHUNG ẢNH VUÔNG tỉ lệ 1:1 (1080x1080), bố cục cân đối gọn trong khung vuông."
    )
    notes.append("Chỉ dựa vào các ảnh đính kèm trong tin nhắn NÀY.")
    notes.append(REALISM)
    notes.append(LOGIC)

    body = prompt.strip()
    if _MODEST.lower() not in body.lower():
        body = f"{body} {_MODEST}"
    return f"{body}\n\n{' '.join(notes)}"


async def generate_one(
    session: AioSession,
    prompt_obj: dict,
    product: Path,
    person: Optional[Path] = None,
    scene: Optional[Path] = None,
    dest: Optional[Path] = None,
    timeout_ms: int = 180000,
    retries: int = 2,
    notable_details=None,
    theme: str = "",
    shop: str = "",
    logo: Optional[Path] = None,
) -> dict:
    """Tạo 1 ảnh, tải về dest. Trả result {type,label,prompt,image,status,error}."""
    p_type = prompt_obj["type"]
    refs = select_refs(p_type, product, person, scene)
    has_person = person is not None and p_type in USE_PERSON_TYPES
    has_scene = scene is not None and p_type in USE_SCENE_TYPES
    final_prompt = _build_final_prompt(
        prompt_obj["prompt"], refs, has_person, has_scene, notable_details,
        theme, shop, logo_img=bool(logo),
    )

    last_err = ""
    for attempt in range(1, retries + 1):
        try:
            session._stop()
            await session.new_chat()
            await session.upload_images(refs)
            await session.type_prompt(final_prompt)
            await session.send()
            await session.page.wait_for_timeout(2000)
            src = await session.wait_for_image(timeout_ms=timeout_ms)
            if not src:
                last_err = "no image"
                continue
            out = Path(dest)
            await session.download_image(src, out)
            try:
                to_square(out)  # ép về vuông 1080x1080
            except Exception:
                pass
            if logo:
                overlay_logo(out, logo)  # dán logo thật vào góc
            return {
                "type": p_type,
                "label": prompt_obj.get("label", p_type),
                "prompt": prompt_obj["prompt"],
                "image": str(out),
                "status": "success",
                "conversation_url": session.conversation_url(),
                "error": "",
            }
        except StopRequested:
            raise                # user bấm Dừng → không retry, đẩy lên trên
        except Exception as e:
            last_err = repr(e)
    return {
        "type": p_type,
        "label": prompt_obj.get("label", p_type),
        "prompt": prompt_obj["prompt"],
        "image": None,
        "status": "error",
        "conversation_url": "",
        "error": last_err,
    }
