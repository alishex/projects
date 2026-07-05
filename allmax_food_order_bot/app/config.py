import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
DB_PATH: str = os.getenv("DB_PATH", "data/orders.db")
ANCHOR_DATE: str = os.getenv("ANCHOR_DATE", "2026-06-21")
ANCHOR_INDEX: int = int(os.getenv("ANCHOR_INDEX", "6"))

DEPARTMENTS = [
    {"key": "boshliqlar", "name": "Boshliqlar",      "emoji": "👔", "env": "ADMIN_BOSHLIQLAR"},
    {"key": "umumiy1",    "name": "Umumiy bo'lim 1", "emoji": "🏢", "env": "ADMIN_UMUMIY1"},
    {"key": "umumiy2",    "name": "Umumiy bo'lim 2", "emoji": "🏢", "env": "ADMIN_UMUMIY2"},
    {"key": "moliya",     "name": "Moliya",           "emoji": "💰", "env": "ADMIN_MOLIYA"},
    {"key": "marketing",  "name": "Marketing",        "emoji": "📢", "env": "ADMIN_MARKETING"},
    {"key": "wms",        "name": "WMS",              "emoji": "📦", "env": "ADMIN_WMS"},
    {"key": "savdo",      "name": "Savdo",            "emoji": "🛒", "env": "ADMIN_SAVDO"},
]

ADMIN_TO_DEPT: dict[int, dict] = {}
for _dept in DEPARTMENTS:
    _env_val = os.getenv(_dept["env"])
    if _env_val:
        ADMIN_TO_DEPT[int(_env_val)] = _dept
