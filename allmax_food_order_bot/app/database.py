import aiosqlite
from datetime import datetime
from typing import Optional
from app.config import DB_PATH

_NOW = lambda: datetime.now().isoformat(sep=" ", timespec="seconds")

DEFAULT_MENU = [
    (1, "Dushanba",   "Kuritsa s gribami & garnir", "Chuchvara"),
    (1, "Seshanba",   "Pyure & go'shtli qayla",     "Akaroshka"),
    (1, "Chorshanba", "Kurka file & garnir",         "Tiftel sho'rva"),
    (1, "Payshanba",  "Choyxona osh",                "Merjimek sho'rva"),
    (1, "Juma",       "Shashlik",                    "Kuksi"),
    (1, "Shanba",     "Tabaka",                      "Mampar"),
    (1, "Yakshanba",  "Kurinny kotlet & garnir",     "Dimlama"),
    (2, "Dushanba",   "Go'sht say",                  "Kurinny bulyon"),
    (2, "Seshanba",   "Kiyevskiy katlet",             "Moshxo'rda"),
    (2, "Chorshanba", "Xonim",                        "Akaroshka"),
    (2, "Payshanba",  "To'y oshi",                   "Qaynatma sho'rva"),
    (2, "Juma",       "Bifshteks",                   "Mampar"),
    (2, "Shanba",     "Tovuq say",                   "Mastava"),
    (2, "Yakshanba",  "Jarkob",                      "Kuksi"),
]


async def init_db():
    import os
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS menu (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                week_number INTEGER NOT NULL,
                day_name    TEXT NOT NULL,
                meal_1      TEXT NOT NULL,
                meal_2      TEXT NOT NULL,
                UNIQUE(week_number, day_name)
            );

            CREATE TABLE IF NOT EXISTS settings (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                anchor_date  TEXT DEFAULT '2026-06-21',
                anchor_index INTEGER DEFAULT 6,
                updated_at   TEXT
            );

            CREATE TABLE IF NOT EXISTS department_orders (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                date         TEXT NOT NULL,
                dept_key     TEXT NOT NULL,
                admin_id     INTEGER NOT NULL,
                meal1_count  INTEGER DEFAULT 0,
                meal2_count  INTEGER DEFAULT 0,
                is_confirmed INTEGER DEFAULT 0,
                created_at   TEXT,
                updated_at   TEXT,
                UNIQUE(date, dept_key)
            );
        """)
        await db.commit()

        row = await (await db.execute("SELECT COUNT(*) FROM menu")).fetchone()
        if row[0] == 0:
            await db.executemany(
                "INSERT OR IGNORE INTO menu(week_number, day_name, meal_1, meal_2) VALUES(?,?,?,?)",
                DEFAULT_MENU,
            )
            await db.commit()

        row = await (await db.execute("SELECT COUNT(*) FROM settings")).fetchone()
        if row[0] == 0:
            await db.execute(
                "INSERT INTO settings(anchor_date, anchor_index, updated_at) VALUES(?,?,?)",
                ("2026-06-21", 6, _NOW())
            )
            await db.commit()


async def get_settings() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute("SELECT * FROM settings LIMIT 1")).fetchone()
        return dict(row) if row else {"anchor_date": "2026-06-21", "anchor_index": 6}


async def get_menu_item(week_number: int, day_name: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM menu WHERE week_number=? AND day_name=?",
            (week_number, day_name)
        )).fetchone()
        return dict(row) if row else None


async def upsert_order(date_str: str, dept_key: str, admin_id: int,
                        meal1_count: int, meal2_count: int, confirmed: bool = False):
    now = _NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO department_orders(date, dept_key, admin_id, meal1_count, meal2_count, is_confirmed, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(date, dept_key) DO UPDATE SET
                admin_id=excluded.admin_id,
                meal1_count=excluded.meal1_count,
                meal2_count=excluded.meal2_count,
                is_confirmed=excluded.is_confirmed,
                updated_at=excluded.updated_at
        """, (date_str, dept_key, admin_id, meal1_count, meal2_count, 1 if confirmed else 0, now, now))
        await db.commit()


async def get_orders_for_date(date_str: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT * FROM department_orders WHERE date=?", (date_str,)
        )).fetchall()
        return [dict(r) for r in rows]


async def get_order(date_str: str, dept_key: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM department_orders WHERE date=? AND dept_key=?",
            (date_str, dept_key)
        )).fetchone()
        return dict(row) if row else None
