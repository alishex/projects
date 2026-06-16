"""Application configuration loaded from the environment."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    admin_id: int
    timezone_name: str
    timezone: ZoneInfo
    database_path: Path
    log_level: str
    base_dir: Path = BASE_DIR
    template_path: Path = BASE_DIR / "assets" / "toliq_ish_vazifalar_template.png"
    reports_dir: Path = BASE_DIR / "generated_reports"
    logs_dir: Path = BASE_DIR / "logs"


def load_settings(env_file: str | Path | None = None) -> Settings:
    load_dotenv(env_file or BASE_DIR / ".env")
    token = os.getenv("BOT_TOKEN", "").strip()
    admin_raw = os.getenv("ADMIN_ID", "").strip()
    if not token or token == "your_telegram_bot_token_here":
        raise RuntimeError("BOT_TOKEN .env faylida haqiqiy Telegram bot tokeni bilan to‘ldirilishi kerak.")
    if not admin_raw or not admin_raw.isdigit():
        raise RuntimeError("ADMIN_ID .env faylida raqamli Telegram user ID bo‘lishi kerak.")
    timezone_name = os.getenv("TIMEZONE", "Asia/Tashkent").strip() or "Asia/Tashkent"
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(f"TIMEZONE topilmadi: {timezone_name}") from exc
    database_raw = os.getenv("DATABASE_PATH", "data/database.sqlite3").strip()
    database_path = Path(database_raw)
    if not database_path.is_absolute():
        database_path = BASE_DIR / database_path
    settings = Settings(
        bot_token=token,
        admin_id=int(admin_raw),
        timezone_name=timezone_name,
        timezone=timezone,
        database_path=database_path,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    if not settings.template_path.exists():
        raise RuntimeError(f"Grafik shablon topilmadi: {settings.template_path}")
    return settings
