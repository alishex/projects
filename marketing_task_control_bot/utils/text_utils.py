"""Human-readable Telegram text formatting."""
from __future__ import annotations

from .constants import PRIORITIES, STATUS_LABELS
from .datetime_utils import format_deadline


def task_display_id(task_number: int | str) -> str:
    if isinstance(task_number, str) and task_number.startswith("#"):
        return task_number
    return f"#{int(task_number):04d}"


def priority_text(priority: str) -> str:
    data = PRIORITIES.get(priority, PRIORITIES["P4"])
    return f"{data['icon']} {data['label']}"


def task_details_text(task, timezone) -> str:
    return (
        "📌 Topshiriq ma’lumotlari\n\n"
        f"🆔 ID: {task_display_id(task.task_number)}\n"
        f"📝 Topshiriq: {task.title}\n"
        f"🚦 Muhimlilik: {priority_text(task.priority)}\n"
        f"📅 Deadline: {format_deadline(task.final_deadline, timezone)}\n"
        f"📍 Status: {STATUS_LABELS.get(task.status, task.status)}"
    )
