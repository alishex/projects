import re

_MLN_RE = re.compile(r"\b(mln|million|млн)\b")
_MING_RE = re.compile(r"\b(ming|минг|k)\b")
_CURRENCY_WORD_RE = re.compile(r"\b(so'm|som|сум|сўм|uzs)\b")
_PLAIN_NUMBER_RE = re.compile(r"^\d+(\.\d+)?$")


def parse_amount(raw: str):
    """Erkin yozilgan summani (minor_units, currency) ga o'giradi.

    minor_units — tiyin (UZS uchun) yoki sent (USD uchun), har doim butun son.
    Namunalar: '50000' -> (5000000, 'UZS'); '1.5 mln' -> (150000000, 'UZS');
    '50 ming' -> (5000000, 'UZS'); '$100' / '100 usd' -> (10000, 'USD').
    Tushunarsiz bo'lsa None qaytaradi.
    """
    if not raw:
        return None
    text = raw.strip().lower().replace(",", ".")

    is_usd = False
    if "$" in text or re.search(r"\busd\b", text) or "dollar" in text:
        is_usd = True
        text = text.replace("$", "").replace("usd", "").replace("dollar", "")
    text = text.strip()

    multiplier = 1
    mln_match = _MLN_RE.search(text)
    ming_match = _MING_RE.search(text)
    if mln_match:
        multiplier = 1_000_000
        text = text[: mln_match.start()].strip()
    elif ming_match:
        multiplier = 1_000
        text = text[: ming_match.start()].strip()
    else:
        text = _CURRENCY_WORD_RE.sub("", text).strip()

    text = text.replace(" ", "")
    if not _PLAIN_NUMBER_RE.match(text):
        return None

    value = float(text) * multiplier
    minor_units = round(value * 100)
    return minor_units, ("USD" if is_usd else "UZS")


async def to_uzs_tiyin(amount_minor: int, currency: str, usd_rate: float):
    """Har qanday valyutadagi minor-unit summani UZS tiyiniga o'giradi.

    USD bo'lsa qaytarilgan ikkinchi qiymat — ishlatilgan kurs (tarixiy aniqlik uchun
    tranzaksiyada saqlanadi, kurs keyinchalik o'zgarsa ham eski yozuv o'zgarmaydi).
    """
    if currency == "UZS":
        return amount_minor, None
    usd_amount = amount_minor / 100
    uzs_tiyin = round(usd_amount * usd_rate * 100)
    return uzs_tiyin, usd_rate
