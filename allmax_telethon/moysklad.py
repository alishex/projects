"""
MoySklad stok tekshiruvi moduli — Showroom filtri.

Muhim:
  - Accept-Encoding: gzip headersiz 415 qaytaradi
  - stock/all da search param ishlamaydi → mahsulot nomi bo'yicha local filter
  - Showroom stoki 60 soniyaga cache qilinadi (har so'rovda 2000 ta yuk yuklanmasin)
"""

import gzip
import json
import logging
import os
import time
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)

_BASE        = "https://api.moysklad.ru/api/remap/1.2"
_TIMEOUT     = 12
_SHOWROOM_ID = "31a6eab6-c9cf-11ef-0a80-18080032558e"
_CACHE_TTL   = 600  # sekund (10 daqiqa)

# Showroom stok keshi: {timestamp: float, items: list[dict]}
_cache: dict = {"ts": 0.0, "items": []}


def _headers() -> dict:
    token = os.getenv("MOYSKLAD_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Accept-Encoding": "gzip",
    }


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
        data = r.read()
        if "gzip" in (r.headers.get("Content-Encoding") or ""):
            data = gzip.decompress(data)
        return json.loads(data)


def _fetch_showroom_stock() -> list[dict]:
    """
    Showroom omboridagi barcha mavjud mahsulotlarni yuklaydi.
    stock > 0 bo'lganlarni qaytaradi. Cache qilinadi.
    API xato bersa — eski cache ishlatiladi (bo'sh qaytarmaydi).
    """
    now = time.monotonic()
    if now - _cache["ts"] < _CACHE_TTL and _cache["items"]:
        return _cache["items"]

    store_href = f"{_BASE}/entity/store/{_SHOWROOM_ID}"
    items: list[dict] = []
    offset = 0
    limit  = 1000

    try:
        while True:
            url = (
                f"{_BASE}/report/stock/all"
                f"?filter=store={store_href}"
                f"&limit={limit}&offset={offset}"
            )
            d = _get(url)
            rows = d.get("rows", [])
            for r in rows:
                # quantity = stock - reserve (sotishga haqiqatan tayyor)
                # stock = jami balans (rezervdagilarni ham o'z ichiga oladi)
                qty = float(r.get("quantity", r.get("stock", 0)))
                if qty <= 0:
                    continue
                raw_price = int(r.get("salePrice", 0))
                if raw_price <= 0:
                    continue  # narxi belgilanmagan — sotilmaydi
                items.append({
                    "name":      r["name"],
                    "price_som": raw_price // 100,
                    "stock":     int(qty),
                    "in_stock":  True,
                })
            total = int(d.get("meta", {}).get("size", 0))
            offset += limit
            if offset >= total or not rows:
                break

        _cache["ts"]    = now
        _cache["items"] = items
        log.info("MoySklad showroom cache yangilandi: %d ta mavjud mahsulot", len(items))
        return items

    except Exception as exc:
        log.warning("MoySklad showroom yuklash xatosi: %s", exc)
        if _cache["items"]:
            log.info("Eski cache ishlatilmoqda: %d ta mahsulot", len(_cache["items"]))
            return _cache["items"]
        return []


# MoySkladdagi mahsulot nomlari o'zbekcha/ruscha aralash —
# mijoz bir tilda so'rasa, ikkinchi tildagi nom ham qidirilsin.
_SYNONYMS: dict[str, list[str]] = {
    "remen":      ["kamar", "belt"],
    "belt":       ["kamar", "remen"],
    "kamar":      ["remen", "belt"],
    "atir":       ["parfum", "adekalon"],
    "parfum":     ["atir", "adekalon"],
    "adekalon":   ["atir", "parfum"],
    "soat":       ["qo'l soat"],
    "часы":       ["qo'l soat", "soat"],
    "ochki":      ["ko'zoynak"],
    "achki":      ["ko'zoynak"],
    "ko'zoynak":  ["ochki"],
    "очки":       ["ko'zoynak", "ochki"],
    "sumka":      ["yon sumka", "bananka"],
    "çanta":      ["sumka", "yon sumka"],
    "kostyum":    ["kastyum", "kastyum-shim"],
    "kastyum":    ["kostyum", "kastyum-shim"],
    "kurtka":     ["vetrovka"],
    "vetrovka":   ["kurtka"],
    "paypoq":     ["носки", "носок"],
    "носки":      ["paypoq"],
    "qo'lqop":    ["перчатки"],
}


def _words_match(words: list[str], product_name: str) -> bool:
    """Har bir so'z mahsulot nomida mavjud bo'lsa True (tartib muhim emas)."""
    name = product_name.lower()
    return all(w in name for w in words)


def check_stock(query: str, top: int = 20) -> list[dict]:
    """
    Showroom omborida query bo'yicha mahsulot qidiradi.

    Qidiruv algoritmi (qatlama):
      1. So'zlar bo'yicha: "qora shim" → "shim" HAM "qora" bo'lgan mahsulot topiladi
         (tartib muhim emas: "Shim Qora #1" ham topiladi)
      2. Synonym: "remen" → "kamar" ham qidiriladi
      3. Fallback: 2+ so'zli query'da natija yo'q bo'lsa, har so'z alohida qidiriladi

    Faqat mavjud (stock > 0) mahsulotlarni qaytaradi.
    Returns: [{"name": str, "price_som": int, "stock": int, "in_stock": bool}]
    """
    if not os.getenv("MOYSKLAD_TOKEN", ""):
        log.warning("MOYSKLAD_TOKEN .env da yo'q — stok tekshiruvi o'tkazib yuborildi")
        return []

    try:
        all_items = _fetch_showroom_stock()
    except Exception as exc:
        log.warning("MoySklad showroom yuklash xatosi: %s", exc)
        return []

    q = query.lower().strip()

    # Synonym expansion: "remen" → ["remen", "kamar", "belt"]
    base_terms = [q] + _SYNONYMS.get(q, [])

    seen: set[str] = set()
    matched: list[dict] = []

    def _add(item: dict):
        if item["name"] not in seen:
            seen.add(item["name"])
            matched.append(item)

    # 1-qadam: har bir term uchun SO'ZLAR BO'YICHA qidiruv (tartibsiz)
    for term in base_terms:
        words = term.split()
        for item in all_items:
            if _words_match(words, item["name"]):
                _add(item)

    # 2-qadam (fallback): 2+ so'zli query'da hech narsa topilmasa,
    # har so'zni ALOHIDA qidirish (keng tarmoq)
    if not matched and len(q.split()) >= 2:
        for word in q.split():
            if len(word) >= 3:  # juda qisqa so'zlarni o'tkazib yuboramiz
                syn_words = [word] + _SYNONYMS.get(word, [])
                for sw in syn_words:
                    for item in all_items:
                        if sw in item["name"].lower():
                            _add(item)

    return matched[:top]


def prewarm():
    """Servis ishga tushganda showroom keshini oldindan yuklaydi."""
    try:
        items = _fetch_showroom_stock()
        log.info("MoySklad prewarm: %d ta mahsulot yuklandi", len(items))
    except Exception as exc:
        log.warning("MoySklad prewarm xatosi: %s", exc)


def format_stock_reply(results: list[dict], query: str) -> str:
    """Agent uchun stok natijalarini formatlaydi."""
    if not results:
        return (
            f"'{query}' showroomda topilmadi. "
            f"Imlo xatosi bo'lishi mumkin — boshqa variant bilan check_stock qayta chaqir "
            f"(masalan to'g'ri yozilishi yoki ruscha). "
            f"2 ta urinishdan keyin ham 0 bo'lsa — mijozga yo'q de."
        )

    lines = ["✅ Showroomda mavjud:"]
    for r in results:
        price = f"{r['price_som']:,} so'm" if r["price_som"] else "narx yo'q"
        lines.append(f"  • {r['name']} — {price}")

    return "\n".join(lines)
