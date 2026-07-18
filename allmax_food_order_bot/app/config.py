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

# Owner panelda (🏢 Bo'limlar / 👑 Ownerlar) dasturchisiz o'zgartirilishi mumkin
# bo'lgan standart vaqtlar — faqat DB'da hali sozlama yo'q bo'lsa ishlatiladi.
DEFAULT_POLL_TIME = "17:00"
DEFAULT_REPORT_TIME = "18:00"

# ── .env'dan BIR MARTALIK migratsiya manbasi ────────────────────────────────
# Quyidagilar endi "jonli" konfiguratsiya EMAS — ular faqat departments/owners/
# settings DB jadvallari hali bo'sh bo'lgan BIRINCHI ishga tushirishda urug'
# (seed) sifatida o'qiladi (database.init_db() ichida). Shundan keyin haqiqiy
# manba — DB, va owner panel orqali o'zgartiriladi. Bu o'zgaruvchilarni to'g'ridan
# -to'g'ri ishlatmang — o'rniga runtime bo'limidagi DEPARTMENTS/OWNER_IDS/GROUP_ID
# dan foydalaning (refresh_runtime_config() bilan to'ldiriladi).
_ENV_SEED_GROUP_ID: int | None = _optional_int_env("GROUP_ID")
_ENV_SEED_OWNER_IDS: list[int] = [
    _id for _id in (_optional_int_env("OWNER_ID_1"), _optional_int_env("OWNER_ID_2"))
    if _id is not None
]
_ENV_SEED_DEPARTMENTS = [
    {"key": "boshliqlar", "name": "Boshliqlar",      "emoji": "👔", "env": "ADMIN_BOSHLIQLAR", "deputy_env": "DEPUTY_BOSHLIQLAR",
     "fixed_meal1": _int_env("FIXED_BOSHLIQLAR_MEAL1", "3"), "fixed_meal2": _int_env("FIXED_BOSHLIQLAR_MEAL2", "2")},
    {"key": "umumiy1",    "name": "Umumiy bo'lim 1", "emoji": "🏢", "env": "ADMIN_UMUMIY1",    "deputy_env": "DEPUTY_UMUMIY1"},
    {"key": "umumiy2",    "name": "Umumiy bo'lim 2", "emoji": "🏢", "env": "ADMIN_UMUMIY2",    "deputy_env": "DEPUTY_UMUMIY2"},
    {"key": "moliya",     "name": "Moliya",           "emoji": "💰", "env": "ADMIN_MOLIYA",     "deputy_env": "DEPUTY_MOLIYA"},
    {"key": "marketing",  "name": "Marketing",        "emoji": "📢", "env": "ADMIN_MARKETING",  "deputy_env": "DEPUTY_MARKETING"},
    {"key": "wms",        "name": "WMS",              "emoji": "📦", "env": "ADMIN_WMS",        "deputy_env": "DEPUTY_WMS"},
    {"key": "savdo",      "name": "Savdo",            "emoji": "🛒", "env": "ADMIN_SAVDO",      "deputy_env": "DEPUTY_SAVDO"},
]
for _dept in _ENV_SEED_DEPARTMENTS:
    _dept["admin_id"] = _optional_int_env(_dept["env"])
    _dept["deputy_id"] = _optional_int_env(_dept["deputy_env"])


# ── Runtime (DB-backed) konfiguratsiya ──────────────────────────────────────
# Bo'sh boshlanadi, main.py'da init_db() dan keyin database.refresh_runtime_config()
# chaqirilib to'ldiriladi, va owner panelda har qanday o'zgarishdan keyin qayta
# yangilanadi (restart shart emas). Boshqa modullar bu nomlarni ENDI to'g'ridan
# -to'g'ri "from app.config import DEPARTMENTS" bilan emas, balki
# "import app.config as cfg" + "cfg.DEPARTMENTS" ko'rinishida o'qishi kerak —
# aks holda keyingi refresh ko'rinmay qoladi (Python import o'sha paytdagi
# qiymatni nusxalab oladi, keyingi qayta tayinlashni kuzatmaydi).
DEPARTMENTS: list = []
DEPT_BY_KEY: dict = {}
ADMIN_DEPTS: dict = {}
DEPUTY_DEPTS: dict = {}
ADMIN_IDS: set = set()
DEPUTY_IDS: set = set()
AUTHORIZED_IDS: set = set()
OWNER_IDS: list = []
GROUP_ID: int | None = None
