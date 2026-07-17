"""Unit test (KHÔNG cần trình duyệt) — logic thuần: JSON, store, refs, lọc prompt.

Chạy:
    python tests/test_unit.py        # runner tự viết
    hoặc: python -m pytest tests/test_unit.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# cho phép import core/ config khi chạy trực tiếp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.jsonutil import parse_json
from core.generator import select_refs, _build_final_prompt
from core.pipeline import _filter_prompts
from core import store


# ---------------------- jsonutil ---------------------- #
def test_parse_plain_json():
    assert parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_with_fence():
    txt = 'Đây là kết quả:\n```json\n{"x": [1,2,3]}\n```\nHết.'
    assert parse_json(txt) == {"x": [1, 2, 3]}


def test_parse_json_embedded_prose():
    txt = 'Chắc chắn rồi! {"type":"thumbnail","ok":true} — xong nhé.'
    assert parse_json(txt) == {"type": "thumbnail", "ok": True}


def test_parse_json_array():
    assert parse_json("prefix [ {\"a\":1}, {\"b\":2} ] suffix") == [{"a": 1}, {"b": 2}]


def test_parse_json_nested_braces_in_string():
    txt = '{"prompt":"dùng {không} placeholder","n":2}'
    assert parse_json(txt) == {"prompt": "dùng {không} placeholder", "n": 2}


def test_parse_json_fail():
    try:
        parse_json("không có json ở đây")
        assert False, "phải raise"
    except ValueError:
        pass


# ---------------------- select_refs ---------------------- #
def test_refs_product_only():
    # detail_info không dùng người/cảnh
    r = select_refs("detail_info", Path("p.png"), Path("person.png"), Path("scene.png"))
    assert r == [Path("p.png")]


def test_refs_person_type():
    r = select_refs("thumbnail", Path("p.png"), Path("person.png"), None)
    assert r == [Path("p.png"), Path("person.png")]


def test_refs_scene_type():
    # how_to_use là loại dùng cảnh (không có ảnh người → chỉ product + scene)
    r = select_refs("how_to_use", Path("p.png"), None, Path("scene.png"))
    assert r == [Path("p.png"), Path("scene.png")]


def test_refs_audience_both():
    # audience dùng cả người + cảnh
    r = select_refs("audience", Path("p.png"), Path("per.png"), Path("sc.png"))
    assert r == [Path("p.png"), Path("per.png"), Path("sc.png")]


def test_refs_person_type_no_person():
    # loại cần người nhưng không có ảnh người → chỉ product
    r = select_refs("thumbnail", Path("p.png"), None, None)
    assert r == [Path("p.png")]


# ---------------------- _build_final_prompt ---------------------- #
def test_final_prompt_single_ref_note():
    fp = _build_final_prompt("Cảnh đẹp.", [Path("p.png")], False, False)
    assert "SẢN PHẨM" in fp
    assert "commercial advertising photography" in fp.lower()


def test_final_prompt_multi_ref_person():
    fp = _build_final_prompt("Cảnh.", [Path("p.png"), Path("per.png")], True, False)
    assert "Ảnh 1 là SẢN PHẨM" in fp
    assert "NGƯỜI MẪU" in fp


def test_final_prompt_no_double_suffix():
    base = "Cảnh. Modest, fully appropriate commercial advertising photography."
    fp = _build_final_prompt(base, [Path("p.png")], False, False)
    assert fp.lower().count("commercial advertising photography") == 1


# ---------------------- _filter_prompts ---------------------- #
def _mk(t):
    return {"type": t, "label": t, "prompt": "x", "content": ""}


def test_filter_keeps_selected_and_order():
    prompts = [_mk("pain_point"), _mk("thumbnail"), _mk("detail_info")]
    out = _filter_prompts(prompts, ["thumbnail", "pain_point", "detail_info"], 9)
    # theo thứ tự PROMPT_TYPE_KEYS: thumbnail(1), pain_point(3), detail_info(7)
    assert [p["type"] for p in out] == ["thumbnail", "pain_point", "detail_info"]


def test_filter_cuts_quantity():
    prompts = [_mk("thumbnail"), _mk("detail_info"), _mk("features")]
    out = _filter_prompts(prompts, ["thumbnail", "detail_info", "features"], 2)
    assert len(out) == 2


def test_filter_drops_unselected():
    prompts = [_mk("thumbnail"), _mk("features")]
    out = _filter_prompts(prompts, ["thumbnail"], 9)
    assert [p["type"] for p in out] == ["thumbnail"]


# ---------------------- store ---------------------- #
def test_store_writes_and_zips():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        sid, d = store.new_session_dir(base)
        assert d.exists()
        prompts = [_mk("thumbnail"), _mk("detail_info")]
        store.write_prompts(d, prompts)
        assert (d / "prompts.txt").exists()
        store.write_seo(d, {"seo_name": "Hair Dryer", "ctr_titles": ["a", "b", "c"],
                            "short_title": "Dryer", "description": "Good product",
                            "keywords": "hair dryer, salon", "category": "Home"},
                        theme="đỏ đen", shop="TNT")
        assert (d / "listing_seo.txt").exists()
        store.write_results(d, {"ok_count": 2})
        assert (d / "results.json").exists()
        # tạo 1 file png giả để zip
        (d / "01_thumbnail.png").write_bytes(b"\x89PNG\r\n")
        z = store.zip_session(d, sid)
        assert z.exists() and z.suffix == ".zip"


# ---------------------- runner tự viết ---------------------- #
def _run_all():
    tests = [(n, f) for n, f in globals().items()
             if n.startswith("test_") and callable(f)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e!r}")
            failed += 1
    print(f"\n==> {passed} passed, {failed} failed / {len(tests)} total")
    return failed == 0


if __name__ == "__main__":
    ok = _run_all()
    sys.exit(0 if ok else 1)
