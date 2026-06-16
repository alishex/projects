from __future__ import annotations

import re
from datetime import datetime
from html import escape as html_escape


def digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_phone(value: str | None) -> str:
    d = digits(value)
    if len(d) >= 9:
        d = d[-9:]
        return "+998" + d if len(d) == 9 else "+" + d
    return value or ""


def valid_birth_date(value: str) -> bool:
    value = value.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(value, fmt)
            return 1950 <= dt.year <= datetime.now().year - 14
        except ValueError:
            continue
    return False


def h(value: object) -> str:
    return html_escape(str(value or "-"), quote=False)


def chunk_text(text: str, limit: int = 3900) -> list[str]:
    text = text or ""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    while text:
        cut = text.rfind("\n", 0, limit)
        if cut < 500:
            cut = limit
        chunks.append(text[:cut].strip())
        text = text[cut:].strip()
    return chunks
