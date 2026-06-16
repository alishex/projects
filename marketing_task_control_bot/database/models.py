"""Small dataclasses representing persisted records."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Employee:
    id: int
    role_name: str
    telegram_user_id: int | None
    is_assigned: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: Any) -> "Employee":
        return cls(
            id=row["id"], role_name=row["role_name"], telegram_user_id=row["telegram_user_id"],
            is_assigned=bool(row["is_assigned"]), created_at=row["created_at"], updated_at=row["updated_at"],
        )


@dataclass(slots=True)
class Task:
    id: int
    task_number: int
    title: str
    short_title: str
    description: str | None
    employee_id: int
    created_by_admin_id: int
    priority: str
    priority_label: str
    proposed_deadline: str | None
    final_deadline: str | None
    status: str
    score: int
    created_at: str
    approved_at: str | None
    completed_at: str | None
    overdue_at: str | None
    cancelled_at: str | None
    employee_role: str | None = None
    employee_telegram_user_id: int | None = None

    @classmethod
    def from_row(cls, row: Any) -> "Task":
        keys = set(row.keys())
        return cls(
            id=row["id"], task_number=row["task_number"], title=row["title"], short_title=row["short_title"],
            description=row["description"], employee_id=row["employee_id"], created_by_admin_id=row["created_by_admin_id"],
            priority=row["priority"], priority_label=row["priority_label"], proposed_deadline=row["proposed_deadline"],
            final_deadline=row["final_deadline"], status=row["status"], score=row["score"], created_at=row["created_at"],
            approved_at=row["approved_at"], completed_at=row["completed_at"], overdue_at=row["overdue_at"],
            cancelled_at=row["cancelled_at"], employee_role=row["employee_role"] if "employee_role" in keys else None,
            employee_telegram_user_id=row["employee_telegram_user_id"] if "employee_telegram_user_id" in keys else None,
        )
