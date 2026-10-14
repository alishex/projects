import aiosqlite

from app.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK(kind IN ('expense','income')),
    amount_tiyin INTEGER NOT NULL,
    orig_amount_tiyin INTEGER NOT NULL,
    orig_currency TEXT NOT NULL DEFAULT 'UZS',
    usd_rate_used REAL,
    method TEXT NOT NULL CHECK(method IN ('cash','card')),
    category TEXT NOT NULL,
    comment TEXT,
    source TEXT NOT NULL DEFAULT 'button' CHECK(source IN ('button','text','voice')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS debts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL CHECK(direction IN ('given','taken')),
    person TEXT NOT NULL,
    amount_tiyin INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'UZS',
    comment TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','closed')),
    created_at TEXT NOT NULL,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS category_limits (
    category TEXT PRIMARY KEY,
    limit_tiyin INTEGER NOT NULL
);
"""

DEFAULT_SETTINGS = {
    "usd_rate": "12700",
    "monthly_limit_tiyin": "0",
    "voice_enabled": "1",
}


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        for key, value in DEFAULT_SETTINGS.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        await db.commit()


def get_db():
    return aiosqlite.connect(DB_PATH)
