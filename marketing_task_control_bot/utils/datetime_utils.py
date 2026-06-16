"""Timezone-safe date helpers for Asia/Tashkent workflows."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .constants import DEADLINE_FORMAT


def now_local(timezone: ZoneInfo) -> datetime:
    return datetime.now(timezone)


def parse_deadline(text: str, timezone: ZoneInfo) -> datetime:
    value = datetime.strptime(text.strip(), DEADLINE_FORMAT)
    return value.replace(tzinfo=timezone)


def format_deadline(value: datetime | str | None, timezone: ZoneInfo) -> str:
    if not value:
        return "—"
    dt = from_db_datetime(value, timezone) if isinstance(value, str) else value.astimezone(timezone)
    return dt.strftime(DEADLINE_FORMAT)


def to_db_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def from_db_datetime(value: str | datetime | None, timezone: ZoneInfo) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone)
    return parsed.astimezone(timezone)
