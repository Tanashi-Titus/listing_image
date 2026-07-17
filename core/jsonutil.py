"""Trích JSON từ câu trả lời của ChatGPT (thường bọc trong ```json ... ```)."""
from __future__ import annotations

import json
import re
from typing import Any


def _clean(s: str) -> str:
    # bỏ dấu phẩy thừa trước } hoặc ]
    s = re.sub(r",(\s*[}\]])", r"\1", s)
    return s


def _escape_ctrl_in_strings(s: str) -> str:
    """Escape ký tự xuống dòng/tab THẬT nằm bên trong chuỗi JSON.

    ChatGPT hay trả JSON có newline thật trong value (vd 'description' nhiều dòng)
    → json.loads coi là JSON hỏng. Ta escape \\n \\r \\t bên trong chuỗi để cứu."""
    out = []
    in_str = False
    esc = False
    for c in s:
        if in_str:
            if esc:
                out.append(c)
                esc = False
                continue
            if c == "\\":
                out.append(c)
                esc = True
                continue
            if c == '"':
                out.append(c)
                in_str = False
                continue
            if c == "\n":
                out.append("\\n")
                continue
            if c == "\r":
                out.append("\\r")
                continue
            if c == "\t":
                out.append("\\t")
                continue
            out.append(c)
        else:
            if c == '"':
                in_str = True
            out.append(c)
    return "".join(out)


def _variants(s: str):
    """Các biến thể để thử parse (bản gốc, bỏ phẩy thừa, escape newline...)."""
    seen = set()
    for v in (s, _clean(s), _escape_ctrl_in_strings(s),
              _clean(_escape_ctrl_in_strings(s))):
        if v and v not in seen:
            seen.add(v)
            yield v


def _balanced_chunks(candidate: str):
    """Sinh các khối {..}/[..] cân bằng đầu tiên (ưu tiên bracket xuất hiện trước)."""
    order = []
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        pos = candidate.find(open_ch)
        if pos != -1:
            order.append((pos, open_ch, close_ch))
    order.sort()
    for _pos, open_ch, close_ch in order:
        start = candidate.find(open_ch)
        if start == -1:
            continue
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(candidate)):
            c = candidate[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    yield candidate[start:i + 1]
                    break


def parse_json(text: str) -> Any:
    """Cố lấy object/array JSON từ text. Raise nếu hoàn toàn không được."""
    if not text or not text.strip():
        raise ValueError("Rỗng, không có JSON")

    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    candidate = fence.group(1).strip() if fence else text.strip()

    for cand in _variants(candidate):
        try:
            return json.loads(cand)
        except Exception:
            pass

    for chunk in _balanced_chunks(candidate):
        for c in _variants(chunk):
            try:
                return json.loads(c)
            except Exception:
                pass
    raise ValueError("Không parse được JSON từ câu trả lời")
