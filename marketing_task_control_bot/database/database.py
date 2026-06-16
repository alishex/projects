"""SQLite connection and first-run schema initialization."""
from __future__ import annotations

import aiosqlite
from pathlib import Path
from datetime import datetime

from utils.constants import EMPLOYEE_ROLES


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name TEXT UNIQUE NOT NULL,
    telegram_user_id INTEGER UNIQUE,
    is_assigned INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_number INTEGER UNIQUE,
    title TEXT NOT NULL,
    short_title TEXT NOT NULL,
    description TEXT,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    created_by_admin_id INTEGER NOT NULL,
    priority TEXT NOT NULL CHECK(priority IN ('P1','P2','P3','P4')),
    priority_label TEXT NOT NULL,
    proposed_deadline TEXT,
    final_deadline TEXT,
    status TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    approved_at TEXT,
    completed_at TEXT,
    overdue_at TEXT,
    cancelled_at TEXT
);
CREATE TABLE IF NOT EXISTS task_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    action_type TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    performed_by_user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    reminder_type TEXT NOT NULL,
    scheduled_for TEXT NOT NULL,
    sent_at TEXT,
    is_sent INTEGER NOT NULL DEFAULT 0,
    UNIQUE(task_id, reminder_type)
);
CREATE TABLE IF NOT EXISTS temporary_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    workflow_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_tasks_status_deadline ON tasks(status, final_deadline);
CREATE INDEX IF NOT EXISTS idx_tasks_employee_status ON tasks(employee_id, status);
CREATE INDEX IF NOT EXISTS idx_history_task ON task_history(task_id);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(self.path)
        self.connection.row_factory = aiosqlite.Row
        await self.connection.execute("PRAGMA foreign_keys = ON")

    @property
    def conn(self) -> aiosqlite.Connection:
        if self.connection is None:
            raise RuntimeError("Database ulanmagan.")
        return self.connection

    async def initialize(self, admin_id: int) -> None:
        await self.conn.executescript(SCHEMA)
        stamp = datetime.utcnow().isoformat()
        for role in EMPLOYEE_ROLES:
            await self.conn.execute(
                "INSERT OR IGNORE INTO employees (role_name, is_assigned, created_at, updated_at) VALUES (?, 0, ?, ?)",
                (role, stamp, stamp),
            )
        await self.conn.execute(
            """INSERT INTO users (telegram_user_id, full_name, role, is_admin, is_active, created_at, updated_at)
               VALUES (?, 'Admin', 'ADMIN', 1, 1, ?, ?)
               ON CONFLICT(telegram_user_id) DO UPDATE SET role='ADMIN', is_admin=1, is_active=1, updated_at=excluded.updated_at""",
            (admin_id, stamp, stamp),
        )
        await self.conn.commit()

    async def close(self) -> None:
        if self.connection:
            await self.connection.close()
            self.connection = None
