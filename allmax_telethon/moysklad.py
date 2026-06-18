"""
MoySklad stok tekshiruvi moduli.

Muhim: api.moysklad.ru Accept-Encoding: gzip headersiz 415 qaytaradi.
Stock filter uchun URL encode qilinmasin (raw URL ishlatiladi).
"""

import gzip
import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Optional

log = logging.getLogger(__name__)

_BASE = "https://api.moysklad.ru/api/remap/1.2"
_TIMEOUT = 10


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


def check_stock(query: str, limit: int = 6) -> list[dict]:
    """
    Mahsulot nomini qidiradi va stok holatini qaytaradi.
    Returns: [{"name": str, "price_som": int, "stock": int, "in_stock": bool}]

    Agar MOYSKLAD_TOKEN yo'q bo'lsa — bo'sh ro'yxat qaytaradi.
    """
    if not os.getenv("MOYSKLAD_TOKEN", ""):
        log.warning("MOYSKLAD_TOKEN .env da yo'q — stok tekshiruvi o'tkazib yuborildi")
        return []

    # 1. Mahsulot qidirish
    search_url = (
        f"{_BASE}/entity/product"
        f"?search={urllib.parse.quote(query, safe='')}&limit={limit}"
    )
    try:
        result = _get(search_url)
    except Exception as exc:
        log.warning("MoySklad qidirish xatosi [%s]: %s", query, exc)
        return []

    rows = result.get("rows", [])
    if not rows:
        return []

    # 2. Batch stok so'rovi (barcha mahsulotlar uchun bitta so'rov)
    # URL encode qilinmaydi — MoySklad raw URL talab qiladi
    hrefs = [p["meta"]["href"].split("?")[0] for p in rows]
    filter_str = ";".join(f"product={h}" for h in hrefs)
    stock_url = f"{_BASE}/report/stock/all?filter={filter_str}"

    stock_map: dict[str, int] = {}
    try:
        sr = _get(stock_url)
        for s in sr.get("rows", []):
            pid = s["meta"]["href"].split("?")[0].split("/")[-1]
            stock_map[pid] = int(s.get("stock", 0))
    except Exception as exc:
        log.warning("MoySklad stok xatosi: %s", exc)

    items = []
    for p in rows:
        pid = p["id"]
        qty = stock_map.get(pid, 0)
        raw_price = p.get("salePrices", [{}])[0].get("value", 0)
        items.append({
            "name":       p["name"],
            "price_som":  int(raw_price) // 100,
            "stock":      qty,
            "in_stock":   qty > 0,
        })
    return items


def format_stock_reply(results: list[dict], query: str) -> str:
    """
    Agent uchun stok natijalarini o'zbek tilida formatlaydi.
    """
    if not results:
        return (
            f"'{query}' bo'yicha MoySkladda hech narsa topilmadi. "
            f"Imlo xatosi bo'lishi mumkin — boshqa variant bilan check_stock qayta chaqir "
            f"(masalan: '{query}' o'rniga to'liqroq yoki to'g'ri imlosi bilan). "
            f"2 ta urinishdan keyin ham 0 bo'lsa — mijozga yo'q de."
        )

    in_stock  = [r for r in results if r["in_stock"]]
    out_stock = [r for r in results if not r["in_stock"]]

    lines: list[str] = []

    if in_stock:
        lines.append("✅ Mavjud mahsulotlar:")
        for r in in_stock:
            price = f"{r['price_som']:,} so'm" if r["price_som"] else "narx yo'q"
            lines.append(f"  • {r['name']} — {price}")

    if out_stock:
        if in_stock:
            lines.append("")
        lines.append("📦 Hozircha tugagan:")
        for r in out_stock:
            lines.append(f"  • {r['name']}")

    return "\n".join(lines)
