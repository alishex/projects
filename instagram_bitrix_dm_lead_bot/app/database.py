from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

from app.utils.time_utils import utc_now_iso

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    igsid TEXT UNIQUE NOT NULL,
    username TEXT,
    full_name TEXT,
    phone TEXT,
    contact_found INTEGER DEFAULT 0,
    template_sent INTEGER DEFAULT 0,
    template_sent_at TEXT,
    manual_outgoing_detected INTEGER DEFAULT 0,
    bitrix_lead_id TEXT,
    bitrix_task_id TEXT,
    telegram_sent INTEGER DEFAULT 0,
    target_detected INTEGER DEFAULT 0,
    target_name TEXT,
    history_json TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conversations_phone ON conversations(phone);
CREATE INDEX IF NOT EXISTS idx_conversations_igsid ON conversations(igsid);

CREATE TABLE IF NOT EXISTS processed_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sent_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL,
    igsid TEXT,
    bitrix_lead_id TEXT,
    bitrix_task_id TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sent_leads_phone ON sent_leads(phone);
"""


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
        log.info("SQLite initialized at %s", self.path)

    def mark_event_processing(self, event_id: str) -> bool:
        if not event_id:
            return True
        try:
            with self.connect() as conn:
                conn.execute(
                    "INSERT INTO processed_events(event_id, created_at) VALUES(?, ?)",
                    (event_id, utc_now_iso()),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def get_conversation(self, igsid: str) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM conversations WHERE igsid=?", (igsid,)).fetchone()

    def upsert_conversation(self, igsid: str, **fields: Any) -> sqlite3.Row:
        existing = self.get_conversation(igsid)
        now = utc_now_iso()
        allowed = {
            "username", "full_name", "phone", "contact_found", "template_sent", "template_sent_at",
            "manual_outgoing_detected", "bitrix_lead_id", "bitrix_task_id", "telegram_sent",
            "target_detected", "target_name", "history_json",
        }
        fields = {k: v for k, v in fields.items() if k in allowed}
        if existing is None:
            columns = ["igsid", "created_at", "updated_at"] + list(fields.keys())
            values = [igsid, now, now] + list(fields.values())
            placeholders = ",".join("?" for _ in values)
            with self.connect() as conn:
                conn.execute(
                    f"INSERT INTO conversations({','.join(columns)}) VALUES({placeholders})",
                    values,
                )
            return self.get_conversation(igsid)  # type: ignore[return-value]
        if fields:
            assigns = ", ".join(f"{key}=?" for key in fields) + ", updated_at=?"
            values = list(fields.values()) + [now, igsid]
            with self.connect() as conn:
                conn.execute(f"UPDATE conversations SET {assigns} WHERE igsid=?", values)
        return self.get_conversation(igsid)  # type: ignore[return-value]

    def append_history(self, igsid: str, role: str, text: str, max_items: int = 30, extra: dict[str, Any] | None = None) -> sqlite3.Row:
        row = self.upsert_conversation(igsid)
        try:
            history = json.loads(row["history_json"] or "[]")
        except json.JSONDecodeError:
            history = []
        item = {"role": role, "text": text, "at": utc_now_iso()}
        if extra:
            item.update(extra)
        history.append(item)
        history = history[-max_items:]
        return self.upsert_conversation(igsid, history_json=json.dumps(history, ensure_ascii=False))

    def get_history(self, igsid: str) -> list[dict[str, Any]]:
        row = self.get_conversation(igsid)
        if not row:
            return []
        try:
            return json.loads(row["history_json"] or "[]")
        except json.JSONDecodeError:
            return []

    def phone_seen_locally(self, phone: str) -> bool:
        with self.connect() as conn:
            row = conn.execute("SELECT id FROM sent_leads WHERE phone=? LIMIT 1", (phone,)).fetchone()
            if row:
                return True
            row = conn.execute(
                "SELECT id FROM conversations WHERE phone=? AND bitrix_lead_id IS NOT NULL LIMIT 1",
                (phone,),
            ).fetchone()
            return bool(row)

    def add_sent_lead(self, phone: str, igsid: str, bitrix_lead_id: str | None, bitrix_task_id: str | None) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO sent_leads(phone, igsid, bitrix_lead_id, bitrix_task_id, created_at) VALUES(?, ?, ?, ?, ?)",
                (phone, igsid, bitrix_lead_id, bitrix_task_id, utc_now_iso()),
            )
