import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0") or "0")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "").strip()
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "").strip()
TELEGRAM_SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "user_session").strip()

COMMAND_BOT_TOKEN = os.getenv("COMMAND_BOT_TOKEN", "").strip()
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "0") or "0")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6").strip()
MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "25") or "25")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Ovozli/video xabarlarni matnga aylantirish (transkripsiya)
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base").strip()
MAX_MEDIA_DURATION_SEC = int(os.getenv("MAX_MEDIA_DURATION_SEC", "600") or "600")
MAX_TRANSCRIBE_PER_CALL = int(os.getenv("MAX_TRANSCRIBE_PER_CALL", "15") or "15")
