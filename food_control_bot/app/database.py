import aiosqlite
from datetime import datetime, date
from typing import Optional
from app.config import DB_PATH

NOW = lambda: datetime.now().isoformat(sep=" ", timespec="seconds")

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
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name   TEXT,
                username    TEXT,
                role        TEXT DEFAULT 'employee',
                is_active   INTEGER DEFAULT 1,
                has_started INTEGER DEFAULT 0,
                created_at  TEXT,
                updated_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id     INTEGER,
                group_id     INTEGER,
                anchor_date  TEXT DEFAULT '2026-06-21',
                anchor_week  INTEGER DEFAULT 1,
                anchor_day   TEXT DEFAULT 'Yakshanba',
                anchor_index INTEGER DEFAULT 6,
                timezone     TEXT DEFAULT 'Asia/Tashkent',
                created_at   TEXT,
                updated_at   TEXT
            );

            CREATE TABLE IF NOT EXISTS menu (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                week_number INTEGER NOT NULL,
                day_name    TEXT NOT NULL,
                meal_1      TEXT NOT NULL,
                meal_2      TEXT NOT NULL,
                UNIQUE(week_number, day_name)
            );

            CREATE TABLE IF NOT EXISTS daily_orders (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                date           TEXT NOT NULL,
                telegram_id    INTEGER NOT NULL,
                meal_1_status  TEXT DEFAULT NULL,
                meal_2_status  TEXT DEFAULT NULL,
                is_confirmed   INTEGER DEFAULT 0,
                created_at     TEXT,
                updated_at     TEXT,
                UNIQUE(date, telegram_id)
            );

            CREATE TABLE IF NOT EXISTS meal_reports (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                date          TEXT NOT NULL,
                telegram_id   INTEGER NOT NULL,
                meal_number   INTEGER NOT NULL,
                video_file_id TEXT,
                created_at    TEXT
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


# ── Users ──────────────────────────────────────────────────────────────────

async def get_user(telegram_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM users WHERE telegram_id=?", (telegram_id,)
        )).fetchone()
        return dict(row) if row else None


async def add_or_update_user(telegram_id: int, full_name: str, username: Optional[str],
                              role: str = "employee", has_started: int = 1):
    now = NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users(telegram_id, full_name, username, role, is_active, has_started, created_at, updated_at)
            VALUES(?,?,?,?,1,?,?,?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                full_name=excluded.full_name,
                username=excluded.username,
                has_started=excluded.has_started,
                updated_at=excluded.updated_at
        """, (telegram_id, full_name, username, role, has_started, now, now))
        await db.commit()


async def add_employee_id(telegram_id: int):
    """Xodim ID ni qo'shadi (hali /start bosmagan bo'lishi mumkin)."""
    now = NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users(telegram_id, full_name, username, role, is_active, has_started, created_at, updated_at)
            VALUES(?,?,?,?,1,0,?,?)
            ON CONFLICT(telegram_id) DO UPDATE SET role='employee', is_active=1, updated_at=excluded.updated_at
        """, (telegram_id, f"User_{telegram_id}", None, "employee", now, now))
        await db.commit()


async def update_user_started(telegram_id: int, full_name: str, username: Optional[str]):
    now = NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET full_name=?, username=?, has_started=1, updated_at=?
            WHERE telegram_id=?
        """, (full_name, username, now, telegram_id))
        await db.commit()


async def get_all_active_users() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT * FROM users WHERE is_active=1"
        )).fetchall()
        return [dict(r) for r in rows]


async def clear_employees():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE role='employee'")
        await db.commit()


# ── Settings ───────────────────────────────────────────────────────────────

async def get_settings() -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute("SELECT * FROM settings LIMIT 1")).fetchone()
        return dict(row) if row else None


async def save_settings(admin_id: int, group_id: Optional[int],
                         anchor_date: str, anchor_week: int,
                         anchor_day: str, anchor_index: int):
    now = NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await (await db.execute("SELECT id FROM settings LIMIT 1")).fetchone()
        if existing:
            await db.execute("""
                UPDATE settings SET admin_id=?, group_id=?, anchor_date=?, anchor_week=?,
                anchor_day=?, anchor_index=?, updated_at=? WHERE id=?
            """, (admin_id, group_id, anchor_date, anchor_week, anchor_day, anchor_index, now, existing[0]))
        else:
            await db.execute("""
                INSERT INTO settings(admin_id, group_id, anchor_date, anchor_week, anchor_day, anchor_index, timezone, created_at, updated_at)
                VALUES(?,?,?,?,?,?,'Asia/Tashkent',?,?)
            """, (admin_id, group_id, anchor_date, anchor_week, anchor_day, anchor_index, now, now))
        await db.commit()


async def update_group_id(group_id: int):
    now = NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE settings SET group_id=?, updated_at=?", (group_id, now))
        await db.commit()


async def update_cycle(anchor_date: str, anchor_week: int, anchor_day: str, anchor_index: int):
    now = NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE settings SET anchor_date=?, anchor_week=?, anchor_day=?, anchor_index=?, updated_at=?
        """, (anchor_date, anchor_week, anchor_day, anchor_index, now))
        await db.commit()


# ── Menu ───────────────────────────────────────────────────────────────────

async def get_menu_item(week_number: int, day_name: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM menu WHERE week_number=? AND day_name=?",
            (week_number, day_name)
        )).fetchone()
        return dict(row) if row else None


async def update_menu_item(week_number: int, day_name: str, meal_1: str, meal_2: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO menu(week_number, day_name, meal_1, meal_2)
            VALUES(?,?,?,?)
            ON CONFLICT(week_number, day_name) DO UPDATE SET meal_1=excluded.meal_1, meal_2=excluded.meal_2
        """, (week_number, day_name, meal_1, meal_2))
        await db.commit()


async def get_all_menu() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT * FROM menu ORDER BY week_number, id"
        )).fetchall()
        return [dict(r) for r in rows]


# ── Daily Orders ───────────────────────────────────────────────────────────

async def get_order(date_str: str, telegram_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM daily_orders WHERE date=? AND telegram_id=?",
            (date_str, telegram_id)
        )).fetchone()
        return dict(row) if row else None


async def upsert_order(date_str: str, telegram_id: int,
                        meal_1_status: Optional[str] = None,
                        meal_2_status: Optional[str] = None,
                        is_confirmed: int = 0):
    now = NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await (await db.execute(
            "SELECT id FROM daily_orders WHERE date=? AND telegram_id=?",
            (date_str, telegram_id)
        )).fetchone()
        if existing:
            await db.execute("""
                UPDATE daily_orders SET meal_1_status=?, meal_2_status=?, is_confirmed=?, updated_at=?
                WHERE date=? AND telegram_id=?
            """, (meal_1_status, meal_2_status, is_confirmed, now, date_str, telegram_id))
        else:
            await db.execute("""
                INSERT INTO daily_orders(date, telegram_id, meal_1_status, meal_2_status, is_confirmed, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?)
            """, (date_str, telegram_id, meal_1_status, meal_2_status, is_confirmed, now, now))
        await db.commit()


async def confirm_order(date_str: str, telegram_id: int,
                         meal_1_status: str, meal_2_status: str):
    now = NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO daily_orders(date, telegram_id, meal_1_status, meal_2_status, is_confirmed, created_at, updated_at)
            VALUES(?,?,?,?,1,?,?)
            ON CONFLICT(date, telegram_id) DO UPDATE SET
                meal_1_status=excluded.meal_1_status,
                meal_2_status=excluded.meal_2_status,
                is_confirmed=1,
                updated_at=excluded.updated_at
        """, (date_str, telegram_id, meal_1_status, meal_2_status, now, now))
        await db.commit()


async def get_orders_for_date(date_str: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT * FROM daily_orders WHERE date=?", (date_str,)
        )).fetchall()
        return [dict(r) for r in rows]


async def reset_day_orders(date_str: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM daily_orders WHERE date=?", (date_str,))
        await db.commit()


# ── Meal Reports ───────────────────────────────────────────────────────────

async def save_meal_report(date_str: str, telegram_id: int,
                            meal_number: int, video_file_id: str):
    now = NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO meal_reports(date, telegram_id, meal_number, video_file_id, created_at)
            VALUES(?,?,?,?,?)
        """, (date_str, telegram_id, meal_number, video_file_id, now))
        await db.commit()


async def get_meal_reports_for_date(date_str: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT * FROM meal_reports WHERE date=?", (date_str,)
        )).fetchall()
        return [dict(r) for r in rows]


async def get_user_meal_report(date_str: str, telegram_id: int,
                                meal_number: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM meal_reports WHERE date=? AND telegram_id=? AND meal_number=?",
            (date_str, telegram_id, meal_number)
        )).fetchone()
        return dict(row) if row else None
