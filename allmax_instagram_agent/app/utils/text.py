from __future__ import annotations

import html
import re
from typing import Any

BAD_NAME_WORDS = {
    "salom", "assalomu", "assalom", "alekum", "narxi", "price", "dostavka", "yetkazib", "kerak",
    "telefon", "raqam", "nomer", "ism", "men", "meni", "menga", "aloqa", "qiling", "bor", "bormi",
}


def compact_text(value: str | None, max_len: int = 5000) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    return text[:max_len]


def html_escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=False)


def clean_name(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"[+\d_@#:/\\|.,;!?()\[\]{}<>]+", " ", value)
    value = re.sub(r"\b(?:ismim|ism|meni|mening|tel|telefon|raqam|nomer|phone|name)\b", " ", value, flags=re.I)
    words = [w.strip(" -—'") for w in value.split() if w.strip(" -—'")]
    clean_words: list[str] = []
    for word in words[:4]:
        if len(word) < 2:
            continue
        if word.lower() in BAD_NAME_WORDS:
            continue
        if not re.search(r"[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳ]", word):
            continue
        clean_words.append(word[:1].upper() + word[1:])
    if not clean_words:
        return None
    return " ".join(clean_words[:3])


def history_to_text(history: list[dict[str, Any]], max_items: int = 30) -> str:
    tail = history[-max_items:]
    lines = []
    for item in tail:
        role = item.get("role", "in")
        text = item.get("text", "")
        if text:
            lines.append(f"{role}: {text}")
    return "\n".join(lines)


def history_to_incoming_text(history: list[dict[str, Any]], max_items: int = 30) -> str:
    """Faqat mijoz (incoming) xabarlarini qaytaradi. Bot/outgoing xabarlarni o'tkazib yuboradi."""
    tail = history[-max_items:]
    lines = []
    for item in tail:
        role = item.get("role", "in")
        text = item.get("text", "")
        if text and role not in ("outgoing", "outgoing_sync"):
            lines.append(text)
    return "\n".join(lines)
