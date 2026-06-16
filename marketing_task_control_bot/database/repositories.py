"""All SQL access lives here so handlers remain small and testable."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from .database import Database
from .models import Employee, Task
from utils.constants import ACTIVE_STATUSES, PRIORITIES


def utcstamp() -> str:
    return datetime.utcnow().isoformat()


class EmployeeRepository:
    def __init__(self, db: Database):
        self.db = db

    async def list_all(self) -> list[Employee]:
        cursor = await self.db.conn.execute("SELECT * FROM employees ORDER BY id")
        return [Employee.from_row(row) for row in await cursor.fetchall()]

    async def get(self, employee_id: int) -> Employee | None:
        cursor = await self.db.conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,))
        row = await cursor.fetchone()
        return Employee.from_row(row) if row else None

    async def get_by_user_id(self, user_id: int) -> Employee | None:
        cursor = await self.db.conn.execute(
            "SELECT * FROM employees WHERE telegram_user_id=? AND is_assigned=1", (user_id,)
        )
        row = await cursor.fetchone()
        return Employee.from_row(row) if row else None

    async def assign(self, employee_id: int, telegram_user_id: int, admin_id: int) -> tuple[bool, str]:
        if telegram_user_id == admin_id:
            return False, "Admin ID xodim lavozimiga biriktirilmaydi."
        cursor = await self.db.conn.execute(
            "SELECT role_name FROM employees WHERE telegram_user_id=? AND id<>?", (telegram_user_id, employee_id)
        )
        existing = await cursor.fetchone()
        if existing:
            return False, f"Bu Telegram User ID allaqachon {existing['role_name']} lavozimiga biriktirilgan."
        current = await self.get(employee_id)
        if current is None:
            return False, "Xodim topilmadi."
        await self.db.conn.execute(
            "UPDATE employees SET telegram_user_id=?, is_assigned=1, updated_at=? WHERE id=?",
            (telegram_user_id, utcstamp(), employee_id),
        )
        await self.db.conn.commit()
        return True, current.role_name

    async def unassign(self, employee_id: int) -> bool:
        cursor = await self.db.conn.execute(
            "UPDATE employees SET telegram_user_id=NULL, is_assigned=0, updated_at=? WHERE id=?", (utcstamp(), employee_id)
        )
        await self.db.conn.commit()
        return cursor.rowcount > 0


class UserRepository:
    def __init__(self, db: Database):
        self.db = db

    async def upsert(self, user_id: int, full_name: str, role: str, is_admin: bool = False) -> None:
        stamp = utcstamp()
        await self.db.conn.execute(
            """INSERT INTO users (telegram_user_id, full_name, role, is_admin, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, 1, ?, ?)
               ON CONFLICT(telegram_user_id) DO UPDATE SET full_name=excluded.full_name, role=excluded.role,
               is_admin=excluded.is_admin, is_active=1, updated_at=excluded.updated_at""",
            (user_id, full_name, role, int(is_admin), stamp, stamp),
        )
        await self.db.conn.commit()


class TaskRepository:
    SELECT_JOIN = """SELECT t.*, e.role_name AS employee_role, e.telegram_user_id AS employee_telegram_user_id
                     FROM tasks t JOIN employees e ON e.id=t.employee_id"""

    def __init__(self, db: Database):
        self.db = db

    async def create(self, title: str, short_title: str, employee_id: int, admin_id: int, priority: str) -> Task:
        stamp = utcstamp()
        label = PRIORITIES[priority]["label"]
        cursor = await self.db.conn.execute(
            """INSERT INTO tasks (title, short_title, description, employee_id, created_by_admin_id, priority,
               priority_label, status, score, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'WAITING_EMPLOYEE_DEADLINE', 0, ?)""",
            (title, short_title, title, employee_id, admin_id, priority, label, stamp),
        )
        task_id = cursor.lastrowid
        await self.db.conn.execute("UPDATE tasks SET task_number=? WHERE id=?", (task_id, task_id))
        await self.add_history(task_id, "CREATED", None, f"{priority}: {short_title}", admin_id, commit=False)
        await self.db.conn.commit()
        task = await self.get(task_id)
        assert task is not None
        return task

    async def get(self, task_id: int) -> Task | None:
        cursor = await self.db.conn.execute(f"{self.SELECT_JOIN} WHERE t.id=?", (task_id,))
        row = await cursor.fetchone()
        return Task.from_row(row) if row else None

    async def list_for_employee(self, employee_id: int, statuses: Iterable[str] | None = None) -> list[Task]:
        params: list[object] = [employee_id]
        sql = f"{self.SELECT_JOIN} WHERE t.employee_id=?"
        if statuses:
            status_list = list(statuses)
            sql += f" AND t.status IN ({','.join('?' for _ in status_list)})"
            params.extend(status_list)
        sql += " ORDER BY t.created_at ASC"
        cursor = await self.db.conn.execute(sql, params)
        return [Task.from_row(row) for row in await cursor.fetchall()]

    async def list_active_all(self) -> list[Task]:
        cursor = await self.db.conn.execute(
            f"{self.SELECT_JOIN} WHERE t.status IN (?, ?) ORDER BY t.created_at ASC", ACTIVE_STATUSES
        )
        return [Task.from_row(row) for row in await cursor.fetchall()]

    async def list_by_status(self, statuses: Iterable[str]) -> list[Task]:
        values = list(statuses)
        sql = f"{self.SELECT_JOIN} WHERE t.status IN ({','.join('?' for _ in values)}) ORDER BY t.created_at DESC"
        cursor = await self.db.conn.execute(sql, values)
        return [Task.from_row(row) for row in await cursor.fetchall()]

    async def list_pending_for_employee_user(self, telegram_user_id: int) -> list[Task]:
        cursor = await self.db.conn.execute(
            f"{self.SELECT_JOIN} WHERE e.telegram_user_id=? AND t.status='WAITING_EMPLOYEE_DEADLINE' ORDER BY t.created_at ASC",
            (telegram_user_id,),
        )
        return [Task.from_row(row) for row in await cursor.fetchall()]

    async def set_proposed_deadline(self, task_id: int, deadline: str, user_id: int) -> None:
        await self.db.conn.execute(
            "UPDATE tasks SET proposed_deadline=?, status='WAITING_ADMIN_APPROVAL' WHERE id=? AND status='WAITING_EMPLOYEE_DEADLINE'",
            (deadline, task_id),
        )
        await self.add_history(task_id, "DEADLINE_PROPOSED", None, deadline, user_id, commit=False)
        await self.db.conn.commit()

    async def approve_deadline(self, task_id: int, deadline: str, admin_id: int, edited: bool = False) -> None:
        task = await self.get(task_id)
        old = task.final_deadline if task else None
        action = "DEADLINE_SET_BY_ADMIN" if edited else "DEADLINE_APPROVED"
        await self.db.conn.execute(
            "UPDATE tasks SET final_deadline=?, status='ACTIVE', approved_at=? WHERE id=?",
            (deadline, utcstamp(), task_id),
        )
        await self.add_history(task_id, action, old, deadline, admin_id, commit=False)
        await self.db.conn.commit()

    async def update_fields(self, task_id: int, user_id: int, **changes: object) -> Task | None:
        allowed = {"title", "short_title", "priority", "priority_label", "employee_id", "final_deadline", "score"}
        changes = {k: v for k, v in changes.items() if k in allowed}
        if not changes:
            return await self.get(task_id)
        old_task = await self.get(task_id)
        if old_task is None:
            return None
        assignments = ", ".join(f"{key}=?" for key in changes)
        await self.db.conn.execute(f"UPDATE tasks SET {assignments} WHERE id=?", (*changes.values(), task_id))
        for key, value in changes.items():
            old_value = getattr(old_task, key)
            if str(old_value) != str(value):
                await self.add_history(task_id, f"UPDATED_{key.upper()}", str(old_value), str(value), user_id, commit=False)
        await self.db.conn.commit()
        return await self.get(task_id)

    async def complete(self, task_id: int, user_id: int) -> Task | None:
        task = await self.get(task_id)
        if task is None or task.status not in ACTIVE_STATUSES:
            return None
        stamp = utcstamp()
        await self.db.conn.execute("UPDATE tasks SET status='COMPLETED', completed_at=? WHERE id=?", (stamp, task_id))
        await self.add_history(task_id, "COMPLETED", task.status, "COMPLETED", user_id, commit=False)
        await self.db.conn.commit()
        return await self.get(task_id)

    async def cancel(self, task_id: int, admin_id: int) -> Task | None:
        task = await self.get(task_id)
        if task is None or task.status in ("COMPLETED", "CANCELLED"):
            return None
        await self.db.conn.execute("UPDATE tasks SET status='CANCELLED', cancelled_at=? WHERE id=?", (utcstamp(), task_id))
        await self.add_history(task_id, "CANCELLED", task.status, "CANCELLED", admin_id, commit=False)
        await self.db.conn.commit()
        return await self.get(task_id)

    async def mark_overdue(self, task_id: int) -> Task | None:
        task = await self.get(task_id)
        if task is None or task.status != "ACTIVE":
            return None
        await self.db.conn.execute("UPDATE tasks SET status='OVERDUE', overdue_at=? WHERE id=?", (utcstamp(), task_id))
        await self.add_history(task_id, "OVERDUE", "ACTIVE", "OVERDUE", task.created_by_admin_id, commit=False)
        await self.db.conn.commit()
        return await self.get(task_id)

    async def persist_score(self, task_id: int, score: int) -> None:
        await self.db.conn.execute("UPDATE tasks SET score=? WHERE id=?", (score, task_id))
        await self.db.conn.commit()

    async def add_history(self, task_id: int, action: str, old_value: str | None, new_value: str | None, user_id: int, commit: bool = True) -> None:
        await self.db.conn.execute(
            "INSERT INTO task_history (task_id, action_type, old_value, new_value, performed_by_user_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (task_id, action, old_value, new_value, user_id, utcstamp()),
        )
        if commit:
            await self.db.conn.commit()

    async def history(self, task_id: int):
        cursor = await self.db.conn.execute("SELECT * FROM task_history WHERE task_id=? ORDER BY created_at ASC", (task_id,))
        return await cursor.fetchall()


class ReminderRepository:
    def __init__(self, db: Database):
        self.db = db

    async def is_sent(self, task_id: int, reminder_type: str) -> bool:
        cursor = await self.db.conn.execute(
            "SELECT is_sent FROM reminders WHERE task_id=? AND reminder_type=?", (task_id, reminder_type)
        )
        row = await cursor.fetchone()
        return bool(row and row["is_sent"])

    async def mark_sent(self, task_id: int, reminder_type: str, scheduled_for: str) -> None:
        stamp = utcstamp()
        await self.db.conn.execute(
            """INSERT INTO reminders (task_id, reminder_type, scheduled_for, sent_at, is_sent)
               VALUES (?, ?, ?, ?, 1)
               ON CONFLICT(task_id, reminder_type) DO UPDATE SET scheduled_for=excluded.scheduled_for,
               sent_at=excluded.sent_at, is_sent=1""",
            (task_id, reminder_type, scheduled_for, stamp),
        )
        await self.db.conn.commit()


class TemporaryMessageRepository:
    def __init__(self, db: Database):
        self.db = db

    async def add(self, chat_id: int, message_id: int, workflow_type: str) -> None:
        await self.db.conn.execute(
            "INSERT INTO temporary_messages (chat_id, message_id, workflow_type, created_at, is_deleted) VALUES (?, ?, ?, ?, 0)",
            (chat_id, message_id, workflow_type, utcstamp()),
        )
        await self.db.conn.commit()

    async def pending(self, chat_id: int, workflow_type: str):
        cursor = await self.db.conn.execute(
            "SELECT * FROM temporary_messages WHERE chat_id=? AND workflow_type=? AND is_deleted=0", (chat_id, workflow_type)
        )
        return await cursor.fetchall()

    async def mark_deleted(self, row_id: int) -> None:
        await self.db.conn.execute("UPDATE temporary_messages SET is_deleted=1 WHERE id=?", (row_id,))
        await self.db.conn.commit()
