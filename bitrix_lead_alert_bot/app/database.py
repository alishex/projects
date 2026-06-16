from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import settings


UTC = timezone.utc


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=30000;")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    lead_id INTEGER PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'pending',
                    source TEXT,
                    first_seen_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    sent_at TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    telegram_message_id INTEGER,
                    payload_json TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_leads_status
                ON leads(status, updated_at);
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    def upsert_pending(self, lead_id: int, source: str, payload: dict[str, Any] | None = None) -> bool:
        """Insert lead as pending if not exists. Returns True when new row created."""
        now = utc_now_iso()
        payload_text = json.dumps(payload or {}, ensure_ascii=False)
        with self.connect() as conn:
            row = conn.execute("SELECT lead_id, status FROM leads WHERE lead_id=?", (lead_id,)).fetchone()
            if row:
                # Keep sent leads untouched. Pending/failed can be refreshed.
                if row["status"] != "sent":
                    conn.execute(
                        """
                        UPDATE leads
                        SET updated_at=?, source=COALESCE(source, ?), payload_json=COALESCE(NULLIF(payload_json, '{}'), ?)
                        WHERE lead_id=?
                        """,
                        (now, source, payload_text, lead_id),
                    )
                return False

            conn.execute(
                """
                INSERT INTO leads(lead_id, status, source, first_seen_at, updated_at, payload_json)
                VALUES(?, 'pending', ?, ?, ?, ?)
                """,
                (lead_id, source, now, now, payload_text),
            )
            return True

    def get_status(self, lead_id: int) -> str | None:
        with self.connect() as conn:
            row = conn.execute("SELECT status FROM leads WHERE lead_id=?", (lead_id,)).fetchone()
            return row["status"] if row else None

    def mark_sent(self, lead_id: int, message_id: int | None, payload: dict[str, Any] | None = None) -> None:
        now = utc_now_iso()
        payload_text = json.dumps(payload or {}, ensure_ascii=False)
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE leads
                SET status='sent', sent_at=?, updated_at=?, last_error=NULL,
                    telegram_message_id=?, payload_json=?
                WHERE lead_id=?
                """,
                (now, now, message_id, payload_text, lead_id),
            )

    def mark_failed(self, lead_id: int, error: str) -> None:
        now = utc_now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE leads
                SET status='failed', updated_at=?, attempts=attempts+1, last_error=?
                WHERE lead_id=?
                """,
                (now, error[:1000], lead_id),
            )

    def mark_skipped(self, lead_id: int, source: str, payload: dict[str, Any] | None = None) -> None:
        now = utc_now_iso()
        payload_text = json.dumps(payload or {}, ensure_ascii=False)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO leads(lead_id, status, source, first_seen_at, updated_at, payload_json)
                VALUES(?, 'skipped', ?, ?, ?, ?)
                """,
                (lead_id, source, now, now, payload_text),
            )



    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return str(row["value"]) if row else default

    def set_setting(self, key: str, value: str | int) -> None:
        now_value = str(value)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO settings(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (key, now_value),
            )

    def get_int_setting(self, key: str, default: int = 0) -> int:
        value = self.get_setting(key)
        if value is None or str(value).strip() == "":
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def get_realtime_checkpoint(self) -> int:
        return self.get_int_setting("realtime_checkpoint_lead_id", 0)

    def set_realtime_checkpoint(self, lead_id: int) -> None:
        current = self.get_realtime_checkpoint()
        if int(lead_id) > current:
            self.set_setting("realtime_checkpoint_lead_id", int(lead_id))

    def skip_pending_up_to(self, max_lead_id: int, reason: str = "realtime_baseline_skip") -> int:
        """Mark old pending/failed leads as skipped so they are not sent after a restart."""
        now = utc_now_iso()
        with self.connect() as conn:
            cur = conn.execute(
                """
                UPDATE leads
                SET status='skipped', source=?, updated_at=?, last_error=NULL
                WHERE lead_id <= ? AND status IN ('pending', 'failed')
                """,
                (reason, now, int(max_lead_id)),
            )
            return int(cur.rowcount or 0)

    def pending_lead_ids(self, limit: int = 100) -> list[int]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT lead_id FROM leads
                WHERE status IN ('pending', 'failed')
                ORDER BY lead_id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [int(row["lead_id"]) for row in rows]

    def max_seen_lead_id(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT MAX(lead_id) AS max_id FROM leads").fetchone()
            return int(row["max_id"] or 0)

    def stats(self) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM leads GROUP BY status"
            ).fetchall()
            return {row["status"]: int(row["count"]) for row in rows}


_db = Database(settings.database_path)


def get_db() -> Database:
    return _db
