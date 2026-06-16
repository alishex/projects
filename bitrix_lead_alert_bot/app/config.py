from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return float(value)


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    telegram_mention_user_id: str = os.getenv("TELEGRAM_MENTION_USER_ID", "")
    telegram_mention_name: str = os.getenv("TELEGRAM_MENTION_NAME", "Mas'ul")

    bitrix_webhook_base_url: str = os.getenv("BITRIX_WEBHOOK_BASE_URL", "")
    bitrix_portal_url: str = os.getenv("BITRIX_PORTAL_URL", "").rstrip("/")
    bitrix_entity_type_id: int = _int("BITRIX_ENTITY_TYPE_ID", 1)  # Lead = 1

    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "")

    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = _int("APP_PORT", 8000)
    timezone: str = os.getenv("TIMEZONE", "Asia/Tashkent")
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

    database_path: Path = Path(os.getenv("DATABASE_PATH", "./data/bot.db"))
    log_file: Path = Path(os.getenv("LOG_FILE", "./logs/bot.log"))

    poll_interval_seconds: int = _int("POLL_INTERVAL_SECONDS", 60)
    poll_lookback_limit: int = _int("POLL_LOOKBACK_LIMIT", 50)
    retry_max_attempts: int = _int("RETRY_MAX_ATTEMPTS", 5)
    retry_base_delay_seconds: int = _int("RETRY_BASE_DELAY_SECONDS", 2)
    request_timeout_seconds: int = _int("REQUEST_TIMEOUT_SECONDS", 20)

    # Default changed to SAFE realtime mode: first launch will NOT send existing Bitrix leads.
    realtime_only_mode: bool = _bool("REALTIME_ONLY_MODE", True)
    poll_send_unknown_on_start: bool = _bool("POLL_SEND_UNKNOWN_ON_START", False)
    telegram_min_delay_seconds: float = _float("TELEGRAM_MIN_DELAY_SECONDS", 1.2)

    def validate(self) -> None:
        missing = []
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.telegram_chat_id:
            missing.append("TELEGRAM_CHAT_ID")
        if not self.telegram_mention_user_id:
            missing.append("TELEGRAM_MENTION_USER_ID")
        if not self.bitrix_webhook_base_url:
            missing.append("BITRIX_WEBHOOK_BASE_URL")
        if missing:
            raise RuntimeError(".env ichida quyidagilar to'ldirilmagan: " + ", ".join(missing))


settings = Settings()
