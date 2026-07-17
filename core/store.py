"""Lưu kết quả 1 session listing: thư mục, prompts.txt, listing_text.txt, results.json, zip."""
from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path
from typing import List

from config import OUTPUT_DIR


def new_session_dir(base: Path = OUTPUT_DIR, prefix: str = "listing") -> tuple[str, Path]:
    sid = f"{prefix}_{time.strftime('%y%m%d_%H%M%S')}"
    d = Path(base) / sid
    d.mkdir(parents=True, exist_ok=True)
    return sid, d


def write_prompts(d: Path, prompts: List[dict]) -> Path:
    lines = []
    for i, p in enumerate(prompts, start=1):
        lines.append(f"[{i:02d}] {p.get('type')} — {p.get('label','')}")
        lines.append(p.get("prompt", ""))
        lines.append("")
    out = Path(d) / "prompts.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# Giá trị "rỗng"/placeholder cần LOẠI khỏi bảng chi tiết (không hiển thị, tránh bịa).
_PLACEHOLDER_VALUES = {
    "", "-", "--", "...", ".", "n/a", "na", "none", "null", "updating",
    "to be updated", "tbd", "unknown", "đang cập nhật", "dang cap nhat",
    "chưa cập nhật", "chua cap nhat", "chưa có", "chua co", "không rõ", "khong ro",
    "không xác định", "khong xac dinh",
}


def clean_seo_attrs(attrs) -> dict:
    """Bỏ các trường rỗng/placeholder ('Đang cập nhật', '-', 'N/A'...) — chỉ giữ
    trường có THÔNG TIN THẬT, tránh bịa thông tin lên bảng chi tiết."""
    if not isinstance(attrs, dict):
        return {}
    out = {}
    for k, v in attrs.items():
        if v is None:
            continue
        sval = str(v).strip()
        if not sval or sval.lower() in _PLACEHOLDER_VALUES:
            continue
        out[k] = v
    return out


def seo_text(seo: dict, language: str = "vi") -> str:
    """Dựng nội dung listing SEO (Từ khóa / Title / Mô tả / Chi tiết).

    language='en' → tiêu đề các mục bằng tiếng Anh; 'vi' → tiếng Việt."""
    seo = seo or {}
    en = (language or "vi").lower().startswith("en")
    h_kw = "SEO KEYWORDS" if en else "TỪ KHÓA SEO"
    h_title = "TITLE (Product name)" if en else "TITLE (Tên sản phẩm)"
    h_desc = "PRODUCT DESCRIPTION" if en else "MÔ TẢ SẢN PHẨM"
    h_detail = "PRODUCT DETAILS" if en else "CHI TIẾT SẢN PHẨM"
    sep = "=" * 60
    lines = [h_kw]
    kws = seo.get("keywords", [])
    if isinstance(kws, str):
        kws = [k.strip() for k in kws.split(",") if k.strip()]
    for k in kws:
        lines.append(f"- {k}")
    lines += [sep, "", h_title, str(seo.get("title", seo.get("seo_name", ""))),
              sep, "", h_desc, str(seo.get("description", "")),
              sep, "", h_detail]
    attrs = clean_seo_attrs(seo.get("attributes", {}))
    for k, v in attrs.items():
        lines.append(f"{k}: {v}")
    lines.append(sep)
    return "\n".join(str(x) for x in lines)


def write_seo(d: Path, seo: dict, theme: str = "", shop: str = "",
              language: str = "vi") -> Path:
    """Ghi bộ listing SEO ra listing_seo.txt (tiêu đề mục theo ngôn ngữ)."""
    out = Path(d) / "listing_seo.txt"
    out.write_text(seo_text(seo or {}, language), encoding="utf-8")
    return out


def write_results(d: Path, data: dict) -> Path:
    out = Path(d) / "results.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def zip_session(d: Path, sid: str) -> Path:
    d = Path(d)
    out = d / f"{sid}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in d.iterdir():
            if f.is_file() and f.suffix.lower() in (".png", ".txt", ".json"):
                z.write(f, f.name)
    return out
