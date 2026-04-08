from __future__ import annotations

import csv
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ActivityRecord:
    record_type: str
    id: int
    tx_type: str
    account_type: str
    currency: str
    to_account_type: str | None
    to_currency: str | None
    amount: float
    category: str
    note: str
    created_at: str


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with closing(self.connect()) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_type TEXT NOT NULL CHECK (tx_type IN ('income', 'expense')),
                    account_type TEXT NOT NULL DEFAULT 'cash',
                    currency TEXT NOT NULL DEFAULT 'UZS',
                    amount REAL NOT NULL CHECK (amount > 0),
                    category TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_account_type TEXT NOT NULL,
                    from_currency TEXT NOT NULL,
                    to_account_type TEXT NOT NULL,
                    to_currency TEXT NOT NULL,
                    amount REAL NOT NULL CHECK (amount > 0),
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            tx_columns = {row['name'] for row in cur.execute("PRAGMA table_info(transactions)").fetchall()}
            if 'account_type' not in tx_columns:
                cur.execute("ALTER TABLE transactions ADD COLUMN account_type TEXT NOT NULL DEFAULT 'cash'")
            if 'currency' not in tx_columns:
                cur.execute("ALTER TABLE transactions ADD COLUMN currency TEXT NOT NULL DEFAULT 'UZS'")
            conn.commit()

    def add_transaction(self, tx_type: str, account_type: str, currency: str, amount: float, category: str, note: str, created_at: str) -> int:
        with closing(self.connect()) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO transactions (tx_type, account_type, currency, amount, category, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tx_type, account_type, currency, amount, category, note, created_at),
            )
            conn.commit()
            return int(cur.lastrowid)

    def add_transfer(self, from_account_type: str, from_currency: str, to_account_type: str, to_currency: str, amount: float, note: str, created_at: str) -> int:
        with closing(self.connect()) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO transfers (from_account_type, from_currency, to_account_type, to_currency, amount, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (from_account_type, from_currency, to_account_type, to_currency, amount, note, created_at),
            )
            conn.commit()
            return int(cur.lastrowid)

    def delete_record_by_id(self, record_type: str, record_id: int) -> ActivityRecord | None:
        matches = self.get_activity_page(limit=1, offset=0, where_clause="record_type = ? AND id = ?", params=(record_type, record_id))
        if not matches:
            return None
        with closing(self.connect()) as conn:
            table = 'transactions' if record_type == 'transaction' else 'transfers'
            conn.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
            conn.commit()
        return matches[0]

    def count_records(self) -> int:
        with closing(self.connect()) as conn:
            tx_count = int(conn.execute("SELECT COUNT(*) AS cnt FROM transactions").fetchone()['cnt'])
            tr_count = int(conn.execute("SELECT COUNT(*) AS cnt FROM transfers").fetchone()['cnt'])
            return tx_count + tr_count

    def get_activity_page(self, limit: int = 10, offset: int = 0, where_clause: str | None = None, params: tuple = ()) -> list[ActivityRecord]:
        query = """
            SELECT * FROM (
                SELECT
                    'transaction' AS record_type,
                    id,
                    tx_type,
                    account_type,
                    currency,
                    NULL AS to_account_type,
                    NULL AS to_currency,
                    amount,
                    category,
                    note,
                    created_at
                FROM transactions
                UNION ALL
                SELECT
                    'transfer' AS record_type,
                    id,
                    'transfer' AS tx_type,
                    from_account_type AS account_type,
                    from_currency AS currency,
                    to_account_type,
                    to_currency,
                    amount,
                    '' AS category,
                    note,
                    created_at
                FROM transfers
            )
        """
        if where_clause:
            query += f" WHERE {where_clause}"
        query += " ORDER BY datetime(created_at) DESC, id DESC LIMIT ? OFFSET ?"
        full_params = params + (limit, offset)
        with closing(self.connect()) as conn:
            rows = conn.execute(query, full_params).fetchall()
        return [self._row_to_activity(row) for row in rows]

    def get_balance_by_currency_account(self) -> dict[str, dict[str, float]]:
        result = {c: {'cash': 0.0, 'card': 0.0} for c in ('UZS', 'USD', 'EUR')}
        with closing(self.connect()) as conn:
            for row in conn.execute(
                "SELECT currency, account_type, COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount ELSE -amount END), 0) AS balance FROM transactions GROUP BY currency, account_type"
            ).fetchall():
                result[str(row['currency'])][str(row['account_type'])] += float(row['balance'])
            for row in conn.execute(
                "SELECT from_currency AS currency, from_account_type AS account_type, COALESCE(SUM(amount), 0) AS total FROM transfers GROUP BY from_currency, from_account_type"
            ).fetchall():
                result[str(row['currency'])][str(row['account_type'])] -= float(row['total'])
            for row in conn.execute(
                "SELECT to_currency AS currency, to_account_type AS account_type, COALESCE(SUM(amount), 0) AS total FROM transfers GROUP BY to_currency, to_account_type"
            ).fetchall():
                result[str(row['currency'])][str(row['account_type'])] += float(row['total'])
        return result

    def get_period_summary(self, start_iso: str, end_iso: str) -> dict:
        summary: dict[str, dict] = {}

        def ensure_entry(currency: str) -> dict:
            return summary.setdefault(
                currency,
                {
                    'income': 0.0,
                    'expense': 0.0,
                    'transfer_in': 0.0,
                    'transfer_out': 0.0,
                    'balance': 0.0,
                    'tx_count': 0,
                    'transfer_count': 0,
                    'accounts': {
                        'cash': {'income': 0.0, 'expense': 0.0, 'transfer_in': 0.0, 'transfer_out': 0.0, 'balance': 0.0},
                        'card': {'income': 0.0, 'expense': 0.0, 'transfer_in': 0.0, 'transfer_out': 0.0, 'balance': 0.0},
                    },
                },
            )

        with closing(self.connect()) as conn:
            for row in conn.execute(
                "SELECT currency, account_type, COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount END), 0) AS income, COALESCE(SUM(CASE WHEN tx_type = 'expense' THEN amount END), 0) AS expense, COUNT(*) AS tx_count FROM transactions WHERE created_at >= ? AND created_at < ? GROUP BY currency, account_type",
                (start_iso, end_iso),
            ).fetchall():
                entry = ensure_entry(str(row['currency']))
                account = str(row['account_type'])
                income = float(row['income'])
                expense = float(row['expense'])
                entry['income'] += income
                entry['expense'] += expense
                entry['tx_count'] += int(row['tx_count'])
                entry['accounts'][account]['income'] += income
                entry['accounts'][account]['expense'] += expense

            for row in conn.execute(
                "SELECT from_currency AS currency, from_account_type AS account_type, COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt FROM transfers WHERE created_at >= ? AND created_at < ? GROUP BY from_currency, from_account_type",
                (start_iso, end_iso),
            ).fetchall():
                entry = ensure_entry(str(row['currency']))
                account = str(row['account_type'])
                total = float(row['total'])
                entry['transfer_out'] += total
                entry['transfer_count'] += int(row['cnt'])
                entry['accounts'][account]['transfer_out'] += total

            for row in conn.execute(
                "SELECT to_currency AS currency, to_account_type AS account_type, COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt FROM transfers WHERE created_at >= ? AND created_at < ? GROUP BY to_currency, to_account_type",
                (start_iso, end_iso),
            ).fetchall():
                entry = ensure_entry(str(row['currency']))
                account = str(row['account_type'])
                total = float(row['total'])
                entry['transfer_in'] += total
                entry['transfer_count'] += int(row['cnt'])
                entry['accounts'][account]['transfer_in'] += total

        for entry in summary.values():
            entry['balance'] = entry['income'] - entry['expense'] + entry['transfer_in'] - entry['transfer_out']
            for acc in entry['accounts'].values():
                acc['balance'] = acc['income'] - acc['expense'] + acc['transfer_in'] - acc['transfer_out']
        return summary

    def get_category_breakdown(self, start_iso: str, end_iso: str, tx_type: str, currency: str) -> list[tuple[str, float]]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT category, COALESCE(SUM(amount), 0) AS total FROM transactions WHERE tx_type = ? AND currency = ? AND created_at >= ? AND created_at < ? GROUP BY category ORDER BY total DESC, category ASC",
                (tx_type, currency, start_iso, end_iso),
            ).fetchall()
        return [(str(r['category']), float(r['total'])) for r in rows]

    def export_csv(self, output_path: str) -> str:
        rows = self.get_activity_page(limit=100000, offset=0)
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Yozuv turi', 'Turi', 'Qayerdan', 'Qayerga', 'Valyuta', 'Maqsad valyuta', 'Summa', 'Kategoriya', 'Izoh', 'Sana'])
            for row in rows:
                if row.record_type == 'transaction':
                    writer.writerow([row.id, 'Tranzaksiya', 'Kirim' if row.tx_type == 'income' else 'Chiqim', 'Naqd' if row.account_type == 'cash' else 'Karta', '', row.currency, '', row.amount, row.category, row.note, row.created_at])
                else:
                    writer.writerow([row.id, 'Transfer', 'Transfer', 'Naqd' if row.account_type == 'cash' else 'Karta', 'Naqd' if row.to_account_type == 'cash' else 'Karta', row.currency, row.to_currency, row.amount, '', row.note, row.created_at])
        return output_path

    @staticmethod
    def _row_to_activity(row: sqlite3.Row) -> ActivityRecord:
        return ActivityRecord(
            record_type=str(row['record_type']),
            id=int(row['id']),
            tx_type=str(row['tx_type']),
            account_type=str(row['account_type']),
            currency=str(row['currency']),
            to_account_type=(str(row['to_account_type']) if row['to_account_type'] is not None else None),
            to_currency=(str(row['to_currency']) if row['to_currency'] is not None else None),
            amount=float(row['amount']),
            category=str(row['category'] or ''),
            note=str(row['note'] or ''),
            created_at=str(row['created_at']),
        )
