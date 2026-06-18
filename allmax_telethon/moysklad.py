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
_CACHE_TTL   = 60  # sekund

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
    stock > 0 bo'lganlarni qaytaradi. 60 soniyaga cache qilinadi.
    """
    now = time.monotonic()
    if now - _cache["ts"] < _CACHE_TTL and _cache["items"]:
        return _cache["items"]

    store_href = f"{_BASE}/entity/store/{_SHOWROOM_ID}"
    items: list[dict] = []
    offset = 0
    limit  = 1000

    while True:
        url = (
            f"{_BASE}/report/stock/all"
            f"?filter=store={store_href}"
            f"&limit={limit}&offset={offset}"
        )
        d = _get(url)
        rows = d.get("rows", [])
        for r in rows:
            qty = float(r.get("stock", 0))
            if qty <= 0:
                continue
            raw_price = int(r.get("price", 0))
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


def check_stock(query: str, top: int = 8) -> list[dict]:
    """
    Showroom omborida query bo'yicha mahsulot qidiradi.
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
    matched = [item for item in all_items if q in item["name"].lower()]

    # Natijalarni qisqartirish: agar juda ko'p variant bo'lsa top ta qaytarish
    return matched[:top]


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
