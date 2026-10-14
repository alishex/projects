import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
NLU_MODEL = os.getenv("NLU_MODEL", "claude-haiku-4-5")
DB_PATH = os.getenv("DB_PATH", "moliya.db")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi — .env faylini tekshiring")
if not OWNER_ID:
    raise RuntimeError("OWNER_ID topilmadi — .env faylini tekshiring")
