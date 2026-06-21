import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
SUPER_ADMIN_ID: int = int(os.getenv("SUPER_ADMIN_ID", "0"))
TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Tashkent")
DB_PATH: str = os.getenv("DB_PATH", "food_control.db")
ANCHOR_DATE: str = os.getenv("ANCHOR_DATE", "2026-06-21")
ANCHOR_WEEK: int = int(os.getenv("ANCHOR_WEEK", "1"))
ANCHOR_DAY: str = os.getenv("ANCHOR_DAY", "Yakshanba")
ANCHOR_INDEX: int = int(os.getenv("ANCHOR_INDEX", "6"))
