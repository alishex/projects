import os
import sys
from dotenv import load_dotenv

load_dotenv()


def _int_env(name: str, default: str) -> int:
    raw = os.getenv(name, default)
    try:
        return int(raw)
    except ValueError:
        print(f"OGOHLANTIRISH: {name}={raw!r} raqam emas, standart qiymat {default!r} ishlatiladi", file=sys.stderr)
        return int(default)


def _optional_int_env(name: str) -> int | None:
    raw = os.getenv(name)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        print(f"OGOHLANTIRISH: {name}={raw!r} raqam emas, e'tiborga olinmadi", file=sys.stderr)
        return None


BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
DB_PATH: str = os.getenv("DB_PATH", "data/orders.db")
ANCHOR_DATE: str = os.getenv("ANCHOR_DATE", "2026-06-21")
ANCHOR_INDEX: int = _int_env("ANCHOR_INDEX", "6")

# Guruh — yakuniy hisobot (ortib qolgan ovqat) doiraviy videosi shu yerga
# yuboriladi. Bo'sh bo'lsa, videoni forward qilishga urinilmaydi (aniq xato
# xabari beriladi).
GROUP_ID: int | None = _optional_int_env("GROUP_ID")

# Ikkita owner — kunlik hisobot (18:00) va feedback ikkalasiga ham teng
# ravishda yuboriladi.
OWNER_IDS: list[int] = [
    _id for _id in (_optional_int_env("OWNER_ID_1"), _optional_int_env("OWNER_ID_2"))
    if _id is not None
]

DEPARTMENTS = [
    {"key": "boshliqlar", "name": "Boshliqlar",      "emoji": "👔", "env": "ADMIN_BOSHLIQLAR", "deputy_env": "DEPUTY_BOSHLIQLAR"},
    {"key": "umumiy1",    "name": "Umumiy bo'lim 1", "emoji": "🏢", "env": "ADMIN_UMUMIY1",    "deputy_env": "DEPUTY_UMUMIY1"},
    {"key": "umumiy2",    "name": "Umumiy bo'lim 2", "emoji": "🏢", "env": "ADMIN_UMUMIY2",    "deputy_env": "DEPUTY_UMUMIY2"},
    {"key": "moliya",     "name": "Moliya",           "emoji": "💰", "env": "ADMIN_MOLIYA",     "deputy_env": "DEPUTY_MOLIYA"},
    {"key": "marketing",  "name": "Marketing",        "emoji": "📢", "env": "ADMIN_MARKETING",  "deputy_env": "DEPUTY_MARKETING"},
    {"key": "wms",        "name": "WMS",              "emoji": "📦", "env": "ADMIN_WMS",        "deputy_env": "DEPUTY_WMS"},
    {"key": "savdo",      "name": "Savdo",            "emoji": "🛒", "env": "ADMIN_SAVDO",      "deputy_env": "DEPUTY_SAVDO"},
]

# Bitta admin (yoki o'rinbosar) bir nechta bo'limga mas'ul bo'lishi mumkin
# (masalan Umumiy bo'lim 1 va 2), shuning uchun bo'lim->odam ko'p-ga-bir;
# ADMIN_DEPTS/DEPUTY_DEPTS esa odam->bo'lim(lar) bir-ko'pga (har bir odam
# uchun ro'yxat qaytaradi).
DEPT_BY_KEY: dict[str, dict] = {}
ADMIN_DEPTS: dict[int, list] = {}
DEPUTY_DEPTS: dict[int, list] = {}

for _dept in DEPARTMENTS:
    _admin_id = _optional_int_env(_dept["env"])
    _deputy_id = _optional_int_env(_dept["deputy_env"])
    _dept["admin_id"] = _admin_id
    _dept["deputy_id"] = _deputy_id
    DEPT_BY_KEY[_dept["key"]] = _dept
    if _admin_id is not None:
        ADMIN_DEPTS.setdefault(_admin_id, []).append(_dept)
    if _deputy_id is not None:
        DEPUTY_DEPTS.setdefault(_deputy_id, []).append(_dept)

ADMIN_IDS = set(ADMIN_DEPTS.keys())
DEPUTY_IDS = set(DEPUTY_DEPTS.keys())
# Bo'lim uchun buyurtma/hisobot/feedback berishga ruxsati bor barcha odamlar —
# asosiy admin va o'rinbosar bo'lim funksiyalarida teng huquqli.
AUTHORIZED_IDS = ADMIN_IDS | DEPUTY_IDS
