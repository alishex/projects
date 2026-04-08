from __future__ import annotations

import csv
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Transaction:
    id: int
    tx_type: str
    account_type: str
    currency: str
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
            columns = {row['name'] for row in cur.execute("PRAGMA table_info(transactions)").fetchall()}
            if 'account_type' not in columns:
                cur.execute("ALTER TABLE transactions ADD COLUMN account_type TEXT NOT NULL DEFAULT 'cash'")
            if 'currency' not in columns:
                cur.execute("ALTER TABLE transactions ADD COLUMN currency TEXT NOT NULL DEFAULT 'UZS'")
            conn.commit()

    def add_transaction(
        self,
        tx_type: str,
        account_type: str,
        currency: str,
        amount: float,
        category: str,
        note: str,
        created_at: str,
    ) -> int:
        with closing(self.connect()) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO transactions (tx_type, account_type, currency, amount, category, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (tx_type, account_type, currency, amount, category, note, created_at),
            )
            conn.commit()
            return int(cur.lastrowid)

    def delete_transaction_by_id(self, transaction_id: int) -> Transaction | None:
        with closing(self.connect()) as conn:
            cur = conn.cursor()
            row = cur.execute(
                "SELECT * FROM transactions WHERE id = ?",
                (transaction_id,),
            ).fetchone()
            if row is None:
                return None
            cur.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            conn.commit()
            return self._row_to_transaction(row)

    def count_transactions(self) -> int:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM transactions").fetchone()
            return int(row['cnt']) if row else 0

    def get_transactions_page(self, limit: int = 8, offset: int = 0) -> list[Transaction]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY datetime(created_at) DESC, id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [self._row_to_transaction(row) for row in rows]

    def get_balance_by_currency_account(self) -> dict[str, dict[str, float]]:
        result = {
            'UZS': {'cash': 0.0, 'card': 0.0},
            'USD': {'cash': 0.0, 'card': 0.0},
            'EUR': {'cash': 0.0, 'card': 0.0},
        }
        with closing(self.connect()) as conn:
            rows = conn.execute(
                """
                SELECT currency, account_type,
                       COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount ELSE -amount END), 0) AS balance
                FROM transactions
                GROUP BY currency, account_type
                """
            ).fetchall()
            for row in rows:
                result[str(row['currency'])][str(row['account_type'])] = float(row['balance'])
        return result

    def get_period_summary(self, start_iso: str, end_iso: str) -> dict:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                """
                SELECT
                    currency,
                    account_type,
                    COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount END), 0) AS income,
                    COALESCE(SUM(CASE WHEN tx_type = 'expense' THEN amount END), 0) AS expense,
                    COUNT(*) AS tx_count
                FROM transactions
                WHERE created_at >= ? AND created_at < ?
                GROUP BY currency, account_type
                ORDER BY currency, account_type
                """,
                (start_iso, end_iso),
            ).fetchall()

            summary: dict[str, dict] = {}
            for row in rows:
                currency = str(row['currency'])
                account_type = str(row['account_type'])
                income = float(row['income'])
                expense = float(row['expense'])
                currency_entry = summary.setdefault(
                    currency,
                    {
                        'income': 0.0,
                        'expense': 0.0,
                        'balance': 0.0,
                        'tx_count': 0,
                        'accounts': {
                            'cash': {'income': 0.0, 'expense': 0.0, 'balance': 0.0, 'tx_count': 0},
                            'card': {'income': 0.0, 'expense': 0.0, 'balance': 0.0, 'tx_count': 0},
                        },
                    },
                )
                acc = currency_entry['accounts'][account_type]
                acc['income'] = income
                acc['expense'] = expense
                acc['balance'] = income - expense
                acc['tx_count'] = int(row['tx_count'])

                currency_entry['income'] += income
                currency_entry['expense'] += expense
                currency_entry['balance'] += income - expense
                currency_entry['tx_count'] += int(row['tx_count'])
            return summary

    def get_category_breakdown(self, start_iso: str, end_iso: str, tx_type: str, currency: str) -> list[tuple[str, float]]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                """
                SELECT category, COALESCE(SUM(amount), 0) AS total
                FROM transactions
                WHERE tx_type = ? AND currency = ? AND created_at >= ? AND created_at < ?
                GROUP BY category
                ORDER BY total DESC, category ASC
                """,
                (tx_type, currency, start_iso, end_iso),
            ).fetchall()
            return [(str(row['category']), float(row['total'])) for row in rows]

    def get_recent_transactions(self, limit: int = 10) -> list[Transaction]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY datetime(created_at) DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [self._row_to_transaction(row) for row in rows]

    def export_csv(self, output_path: str) -> str:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT id, tx_type, account_type, currency, amount, category, note, created_at FROM transactions ORDER BY datetime(created_at) DESC, id DESC"
            ).fetchall()

        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Turi', 'Hisob', 'Valyuta', 'Summa', 'Kategoriya', 'Izoh', 'Sana'])
            for row in rows:
                writer.writerow([
                    row['id'],
                    'Kirim' if row['tx_type'] == 'income' else 'Chiqim',
                    'Naqd' if row['account_type'] == 'cash' else 'Karta',
                    row['currency'],
                    row['amount'],
                    row['category'],
                    row['note'],
                    row['created_at'],
                ])
        return output_path

    @staticmethod
    def _row_to_transaction(row: sqlite3.Row) -> Transaction:
        return Transaction(
            id=int(row['id']),
            tx_type=str(row['tx_type']),
            account_type=str(row['account_type']),
            currency=str(row['currency']),
            amount=float(row['amount']),
            category=str(row['category']),
            note=str(row['note'] or ''),
            created_at=str(row['created_at']),
        )
