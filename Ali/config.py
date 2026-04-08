from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


@dataclass(frozen=True)
class Settings:
    bot_token: str
    owner_telegram_id: int
    db_path: str
    timezone: str



def get_settings() -> Settings:
    token = os.getenv('BOT_TOKEN', '').strip()
    owner_raw = os.getenv('OWNER_TELEGRAM_ID', '').strip()
    db_path = os.getenv('DB_PATH', str(BASE_DIR / 'finance_bot.db')).strip()
    timezone = os.getenv('TIMEZONE', 'Asia/Tashkent').strip()

    if not token:
        raise RuntimeError('BOT_TOKEN .env faylga yozilmagan.')
    if not owner_raw:
        raise RuntimeError('OWNER_TELEGRAM_ID .env faylga yozilmagan.')

    try:
        owner_id = int(owner_raw)
    except ValueError as exc:
        raise RuntimeError('OWNER_TELEGRAM_ID son bo\'lishi kerak.') from exc

    return Settings(
        bot_token=token,
        owner_telegram_id=owner_id,
        db_path=db_path,
        timezone=timezone,
    )
