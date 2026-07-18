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


BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
OWNER_ID: int = _int_env("OWNER_ID", "0")
DB_PATH: str = os.getenv("DB_PATH", "data/orders.db")
ANCHOR_DATE: str = os.getenv("ANCHOR_DATE", "2026-06-21")
ANCHOR_INDEX: int = _int_env("ANCHOR_INDEX", "6")

DEPARTMENTS = [
    {"key": "boshliqlar", "name": "Boshliqlar",      "emoji": "👔", "env": "ADMIN_BOSHLIQLAR"},
    {"key": "umumiy1",    "name": "Umumiy bo'lim 1", "emoji": "🏢", "env": "ADMIN_UMUMIY1"},
    {"key": "umumiy2",    "name": "Umumiy bo'lim 2", "emoji": "🏢", "env": "ADMIN_UMUMIY2"},
    {"key": "moliya",     "name": "Moliya",           "emoji": "💰", "env": "ADMIN_MOLIYA"},
    {"key": "marketing",  "name": "Marketing",        "emoji": "📢", "env": "ADMIN_MARKETING"},
    {"key": "wms",        "name": "WMS",              "emoji": "📦", "env": "ADMIN_WMS"},
    {"key": "savdo",      "name": "Savdo",            "emoji": "🛒", "env": "ADMIN_SAVDO"},
]

# Bitta admin bir nechta bo'limga mas'ul bo'lishi mumkin (masalan Umumiy
# bo'lim 1 va 2), shuning uchun bo'lim->admin ko'p-ga-bir; ADMIN_DEPTS esa
# admin->bo'lim(lar) bir-ko'pga (har bir admin uchun ro'yxat qaytaradi).
DEPT_BY_KEY: dict[str, dict] = {}
ADMIN_DEPTS: dict[int, list] = {}

for _dept in DEPARTMENTS:
    _env_val = os.getenv(_dept["env"])
    _admin_id = None
    if _env_val:
        try:
            _admin_id = int(_env_val)
        except ValueError:
            print(f"OGOHLANTIRISH: {_dept['env']}={_env_val!r} raqam emas, e'tiborga olinmadi", file=sys.stderr)
    _dept["admin_id"] = _admin_id
    DEPT_BY_KEY[_dept["key"]] = _dept
    if _admin_id is not None:
        ADMIN_DEPTS.setdefault(_admin_id, []).append(_dept)

ADMIN_IDS = set(ADMIN_DEPTS.keys())
