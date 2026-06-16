from __future__ import annotations

import re
from typing import Optional

UZ_CODES = {
    "33", "50", "55", "71", "77", "78", "88", "90", "91", "93", "94", "95", "97", "98", "99"
}

PHONE_CANDIDATE_RE = re.compile(
    r"(?:(?:\+?998)[\s\-\.\(\)]*)?(?:\d[\s\-\.\(\)]*){9,12}"
)


def normalize_phone(value: str | None) -> Optional[str]:
    if not value:
        return None
    digits = re.sub(r"\D+", "", value)

    if len(digits) > 12:
        # Try to find Uzbekistan number inside longer text, e.g. +998901234567.
        match = re.search(r"998\d{9}", digits)
        if match:
            digits = match.group(0)
        else:
            match = re.search(r"\d{9}$", digits)
            if match:
                digits = match.group(0)

    if digits.startswith("00998") and len(digits) == 14:
        digits = digits[2:]

    if digits.startswith("998") and len(digits) == 12:
        local = digits[3:]
    elif len(digits) == 9:
        local = digits
        digits = "998" + local
    elif len(digits) == 10 and digits.startswith("0"):
        local = digits[1:]
        digits = "998" + local
    else:
        return None

    if len(local) != 9 or local[:2] not in UZ_CODES:
        return None
    return "+" + digits


def extract_phone(text: str | None) -> Optional[str]:
    if not text:
        return None
    for candidate in PHONE_CANDIDATE_RE.findall(text):
        phone = normalize_phone(candidate)
        if phone:
            return phone
    return normalize_phone(text)


def phone_digits(phone: str | None) -> str:
    return re.sub(r"\D+", "", phone or "")


def format_phone_local(phone: str | None) -> str:
    normalized = normalize_phone(phone or "") or phone or ""
    digits = phone_digits(normalized)
    if digits.startswith("998") and len(digits) == 12:
        local = digits[3:]
        return f"{local[:2]} {local[2:5]} {local[5:7]} {local[7:9]}"
    return phone or ""


def remove_phone(text: str, phone: str | None = None) -> str:
    result = text or ""
    if phone:
        raw = phone_digits(phone)
        variants = {phone, raw, raw[3:] if raw.startswith("998") else raw}
        for variant in variants:
            if variant:
                result = result.replace(variant, " ")
    result = PHONE_CANDIDATE_RE.sub(" ", result)
    return re.sub(r"\s+", " ", result).strip()
