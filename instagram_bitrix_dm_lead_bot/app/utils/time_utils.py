from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat(timespec="seconds")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def format_for_telegram(dt: datetime | None = None, offset_hours: int = 5) -> str:
    dt = dt or utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(timezone(timedelta(hours=offset_hours)))
    return local.strftime("%d.%m.%Y %H:%M")


def deadline_after_hours(hours: int) -> str | None:
    if hours <= 0:
        return None
    return (utc_now() + timedelta(hours=hours)).isoformat(timespec="seconds")
