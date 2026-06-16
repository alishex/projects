"""Eisenhower priority scoring and deterministic ordering."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from utils.constants import PRIORITIES
from utils.datetime_utils import from_db_datetime


def _value(task: Any, name: str, default=None):
    return task.get(name, default) if isinstance(task, dict) else getattr(task, name, default)


def calculate_task_score(task: Any, now: datetime, timezone: ZoneInfo | None = None) -> int:
    timezone = timezone or ZoneInfo("Asia/Tashkent")
    score = PRIORITIES.get(_value(task, "priority", "P4"), PRIORITIES["P4"])["score"]
    deadline = from_db_datetime(_value(task, "final_deadline"), timezone)
    status = _value(task, "status", "ACTIVE")
    if status == "OVERDUE" or (deadline is not None and deadline < now and status in ("ACTIVE", "OVERDUE")):
        return score + 1000
    if deadline is None:
        return score
    remaining = deadline - now
    if remaining <= timedelta(hours=24):
        score += 80
    elif remaining <= timedelta(days=3):
        score += 50
    elif remaining <= timedelta(days=7):
        score += 20
    return score


def _created(task: Any, timezone: ZoneInfo) -> datetime:
    return from_db_datetime(_value(task, "created_at"), timezone) or datetime.max.replace(tzinfo=timezone)


def _deadline(task: Any, timezone: ZoneInfo) -> datetime:
    return from_db_datetime(_value(task, "final_deadline"), timezone) or datetime.max.replace(tzinfo=timezone)


def sort_tasks(tasks: Iterable[Any], now: datetime, timezone: ZoneInfo | None = None) -> list[Any]:
    timezone = timezone or ZoneInfo("Asia/Tashkent")
    return sorted(
        tasks,
        key=lambda task: (-calculate_task_score(task, now, timezone), _deadline(task, timezone), _created(task, timezone)),
    )


def sort_tasks_for_matrix(tasks: Iterable[Any], now: datetime, timezone: ZoneInfo | None = None) -> list[Any]:
    """Within one cell: overdue first, then nearest deadline, then oldest created record."""
    timezone = timezone or ZoneInfo("Asia/Tashkent")
    return sorted(
        tasks,
        key=lambda task: (
            0 if (_value(task, "status") == "OVERDUE" or _deadline(task, timezone) < now) else 1,
            _deadline(task, timezone),
            _created(task, timezone),
        ),
    )
