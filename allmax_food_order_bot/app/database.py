import aiosqlite
from datetime import datetime
from typing import Optional
from app.config import DB_PATH, ANCHOR_DATE, ANCHOR_INDEX
import app.config as cfg

_NOW = lambda: datetime.now().isoformat(sep=" ", timespec="seconds")

DEFAULT_MENU = [
    (1, "Dushanba",   "Qozon kabob tovuqli", "Qozon kabob tovuqli"),
    (1, "Seshanba",   "Xonim",               "Xonim"),
    (1, "Chorshanba", "Moxora",              "Moxora"),
    (1, "Payshanba",  "To'y oshi",           "To'y oshi"),
    (1, "Juma",       "Kviski & garnir",     "Kviski & garnir"),
    (1, "Shanba",     "Mampar",              "Mampar"),
    (1, "Yakshanba",  "Bulg'or dolma",       "Bulg'or dolma"),
    (2, "Dushanba",   "Bifshteks",           "Bifshteks"),
    (2, "Seshanba",   "Moshxo'rda",          "Moshxo'rda"),
    (2, "Chorshanba", "Chixanbili",          "Chixanbili"),
    (2, "Payshanba",  "Choyxona palov",      "Choyxona palov"),
    (2, "Juma",       "Chuchvara",           "Chuchvara"),
    (2, "Shanba",     "Bedro & garnir",      "Bedro & garnir"),
    (2, "Yakshanba",  "Qovurma lag'mon",     "Qovurma lag'mon"),
    (3, "Dushanba",   "Dimlama",             "Dimlama"),
    (3, "Seshanba",   "Loli kabob",          "Loli kabob"),
    (3, "Chorshanba", "Xonim",               "Xonim"),
    (3, "Payshanba",  "Tiftel shorva",       "Tiftel shorva"),
    (3, "Juma",       "To'y oshi",           "To'y oshi"),
    (3, "Shanba",     "Tovuq say",           "Tovuq say"),
    (3, "Yakshanba",  "Mampar",              "Mampar"),
]


async def _ensure_column(db, table: str, column: str, coltype_default: str):
    """ALTER TABLE ... ADD COLUMN faqat ustun hali mavjud bo'lmasa (qayta ishga tushirishda xavfsiz)."""
    cols = await (await db.execute(f"PRAGMA table_info({table})")).fetchall()
    existing = {c[1] for c in cols}
    if column not in existing:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype_default}")


async def init_db():
    import os
    dirname = os.path.dirname(DB_PATH)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
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
                anchor_date  TEXT,
                anchor_index INTEGER,
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

            CREATE TABLE IF NOT EXISTS departments (
                key          TEXT PRIMARY KEY,
                name         TEXT NOT NULL,
                emoji        TEXT NOT NULL DEFAULT '🏢',
                admin_id     INTEGER,
                deputy_id    INTEGER,
                fixed_meal1  INTEGER,
                fixed_meal2  INTEGER,
                sort_order   INTEGER DEFAULT 0,
                created_at   TEXT,
                updated_at   TEXT
            );

            CREATE TABLE IF NOT EXISTS owners (
                telegram_id INTEGER PRIMARY KEY,
                full_name   TEXT,
                created_at  TEXT
            );
        """)
        await db.commit()

        await _ensure_column(db, "settings", "group_id", "INTEGER")
        await _ensure_column(db, "settings", "poll_time", f"TEXT DEFAULT '{cfg.DEFAULT_POLL_TIME}'")
        await _ensure_column(db, "settings", "report_time", f"TEXT DEFAULT '{cfg.DEFAULT_REPORT_TIME}'")
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
                "INSERT INTO settings(anchor_date, anchor_index, group_id, poll_time, report_time, updated_at) "
                "VALUES(?,?,?,?,?,?)",
                (ANCHOR_DATE, ANCHOR_INDEX, cfg._ENV_SEED_GROUP_ID, cfg.DEFAULT_POLL_TIME, cfg.DEFAULT_REPORT_TIME, _NOW())
            )
            await db.commit()
        else:
            # Eski qatorda group_id ustuni yangi qo'shilgan bo'lishi mumkin (hali NULL) —
            # birinchi migratsiyada .env'dagi GROUP_ID bilan to'ldiramiz.
            existing = await (await db.execute("SELECT group_id FROM settings LIMIT 1")).fetchone()
            if existing and existing[0] is None and cfg._ENV_SEED_GROUP_ID is not None:
                await db.execute("UPDATE settings SET group_id=? WHERE group_id IS NULL", (cfg._ENV_SEED_GROUP_ID,))
                await db.commit()

        # Bo'limlar/ownerlar jadvali BO'SH bo'lsa — bu birinchi marta yangi
        # schema bilan ishga tushish, .env'dagi joriy qiymatlardan bir martalik
        # migratsiya qilamiz (mavjud tayinlovlar yo'qolmasligi uchun).
        row = await (await db.execute("SELECT COUNT(*) FROM departments")).fetchone()
        if row[0] == 0:
            now = _NOW()
            for i, d in enumerate(cfg._ENV_SEED_DEPARTMENTS):
                await db.execute(
                    "INSERT INTO departments(key, name, emoji, admin_id, deputy_id, fixed_meal1, fixed_meal2, sort_order, created_at, updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (d["key"], d["name"], d["emoji"], d.get("admin_id"), d.get("deputy_id"),
                     d.get("fixed_meal1"), d.get("fixed_meal2"), i, now, now)
                )
            await db.commit()

        row = await (await db.execute("SELECT COUNT(*) FROM owners")).fetchone()
        if row[0] == 0:
            now = _NOW()
            for oid in cfg._ENV_SEED_OWNER_IDS:
                await db.execute(
                    "INSERT OR IGNORE INTO owners(telegram_id, full_name, created_at) VALUES(?,?,?)",
                    (oid, f"Owner_{oid}", now)
                )
            await db.commit()


async def refresh_runtime_config():
    """DB'dagi departments/owners/settings.group_id ni app.config runtime
    atributlariga yuklaydi — owner panelda har qanday CRUD amalidan keyin
    qayta chaqiriladi, restart shart emas (food_control_bot'dagi
    refresh_admin_ids() bilan bir xil naqsh)."""
    depts = await get_departments()
    dept_by_key: dict = {}
    admin_depts: dict = {}
    deputy_depts: dict = {}
    for d in depts:
        dept_by_key[d["key"]] = d
        if d.get("admin_id") is not None:
            admin_depts.setdefault(d["admin_id"], []).append(d)
        if d.get("deputy_id") is not None:
            deputy_depts.setdefault(d["deputy_id"], []).append(d)

    cfg.DEPARTMENTS = depts
    cfg.DEPT_BY_KEY = dept_by_key
    cfg.ADMIN_DEPTS = admin_depts
    cfg.DEPUTY_DEPTS = deputy_depts
    cfg.ADMIN_IDS = set(admin_depts.keys())
    cfg.DEPUTY_IDS = set(deputy_depts.keys())
    cfg.AUTHORIZED_IDS = cfg.ADMIN_IDS | cfg.DEPUTY_IDS

    cfg.OWNER_IDS = [o["telegram_id"] for o in await get_owners()]

    settings = await get_settings()
    cfg.GROUP_ID = settings.get("group_id") if settings else None


async def get_settings() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute("SELECT * FROM settings LIMIT 1")).fetchone()
        return dict(row) if row else {"anchor_date": ANCHOR_DATE, "anchor_index": ANCHOR_INDEX}


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


async def update_cycle(anchor_date: str, anchor_index: int):
    now = _NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE settings SET anchor_date=?, anchor_index=?, updated_at=?",
            (anchor_date, anchor_index, now)
        )
        await db.commit()


async def update_schedule_times(poll_time: Optional[str] = None, report_time: Optional[str] = None):
    """poll_time / report_time — 'HH:MM' formatida. Faqat berilgan qiymat yangilanadi."""
    now = _NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        if poll_time is not None:
            await db.execute("UPDATE settings SET poll_time=?, updated_at=?", (poll_time, now))
        if report_time is not None:
            await db.execute("UPDATE settings SET report_time=?, updated_at=?", (report_time, now))
        await db.commit()


async def update_group_id(group_id: int):
    now = _NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE settings SET group_id=?, updated_at=?", (group_id, now))
        await db.commit()


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


# ── Departments (owner panel) ────────────────────────────────────────────────

async def get_departments() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT * FROM departments ORDER BY sort_order, rowid"
        )).fetchall()
        return [dict(r) for r in rows]


async def get_department(key: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM departments WHERE key=?", (key,)
        )).fetchone()
        return dict(row) if row else None


async def add_department(key: str, name: str, emoji: str):
    now = _NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute("SELECT COALESCE(MAX(sort_order), -1) FROM departments")).fetchone()
        next_order = (row[0] or -1) + 1
        await db.execute(
            "INSERT INTO departments(key, name, emoji, sort_order, created_at, updated_at) VALUES(?,?,?,?,?,?)",
            (key, name, emoji, next_order, now, now)
        )
        await db.commit()


async def delete_department(key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM departments WHERE key=?", (key,))
        await db.commit()


async def set_department_admin(key: str, admin_id: Optional[int]):
    now = _NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE departments SET admin_id=?, updated_at=? WHERE key=?",
            (admin_id, now, key)
        )
        await db.commit()


async def set_department_deputy(key: str, deputy_id: Optional[int]):
    now = _NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE departments SET deputy_id=?, updated_at=? WHERE key=?",
            (deputy_id, now, key)
        )
        await db.commit()


async def set_department_fixed(key: str, fixed_meal1: Optional[int], fixed_meal2: Optional[int]):
    """fixed_meal1/2 = None qilib qo'yish — bo'limni 'doimiy son'dan 'admin so'raladigan'
    turkumga qaytaradi (va aksincha, raqam berilsa doimiy turkumga o'tadi)."""
    now = _NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE departments SET fixed_meal1=?, fixed_meal2=?, updated_at=? WHERE key=?",
            (fixed_meal1, fixed_meal2, now, key)
        )
        await db.commit()


# ── Owners (owner panel) ──────────────────────────────────────────────────────

async def get_owners() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT * FROM owners ORDER BY rowid"
        )).fetchall()
        return [dict(r) for r in rows]


async def add_owner(telegram_id: int, full_name: Optional[str] = None):
    now = _NOW()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO owners(telegram_id, full_name, created_at) VALUES(?,?,?) "
            "ON CONFLICT(telegram_id) DO UPDATE SET full_name=excluded.full_name",
            (telegram_id, full_name or f"Owner_{telegram_id}", now)
        )
        await db.commit()


async def remove_owner(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM owners WHERE telegram_id=?", (telegram_id,))
        await db.commit()
