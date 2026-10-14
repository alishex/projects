from app.database import get_db
from app.categories import category_label
from app.utils import now, period_bounds


async def add_transaction(kind, amount_tiyin, orig_amount_tiyin, orig_currency,
                           usd_rate_used, method, category, comment, source="button"):
    async with get_db() as db:
        await db.execute(
            """INSERT INTO transactions
               (kind, amount_tiyin, orig_amount_tiyin, orig_currency, usd_rate_used,
                method, category, comment, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (kind, amount_tiyin, orig_amount_tiyin, orig_currency, usd_rate_used,
             method, category, comment, source, now().isoformat()),
        )
        await db.commit()


async def get_summary(period: str):
    start, end = period_bounds(period)
    async with get_db() as db:
        async with db.execute(
            """SELECT kind, method, SUM(amount_tiyin) FROM transactions
               WHERE created_at >= ? AND created_at <= ?
               GROUP BY kind, method""",
            (start.isoformat(), end.isoformat()),
        ) as cur:
            rows = await cur.fetchall()

    result = {
        "income": {"cash": 0, "card": 0},
        "expense": {"cash": 0, "card": 0},
    }
    for kind, method, total in rows:
        result[kind][method] = total or 0
    for kind in ("income", "expense"):
        result[kind]["total"] = result[kind]["cash"] + result[kind]["card"]
    result["balance"] = result["income"]["total"] - result["expense"]["total"]
    return result, start, end


async def get_category_breakdown(period: str, kind: str):
    start, end = period_bounds(period)
    async with get_db() as db:
        async with db.execute(
            """SELECT category, SUM(amount_tiyin) FROM transactions
               WHERE kind = ? AND created_at >= ? AND created_at <= ?
               GROUP BY category ORDER BY SUM(amount_tiyin) DESC""",
            (kind, start.isoformat(), end.isoformat()),
        ) as cur:
            rows = await cur.fetchall()
    return [(category_label(kind, cat), total) for cat, total in rows]


async def get_recent(limit=10):
    async with get_db() as db:
        async with db.execute(
            """SELECT kind, amount_tiyin, orig_amount_tiyin, orig_currency, method,
                      category, comment, created_at
               FROM transactions ORDER BY id DESC LIMIT ?""",
            (limit,),
        ) as cur:
            return await cur.fetchall()


async def get_all_for_export():
    async with get_db() as db:
        async with db.execute(
            """SELECT id, kind, amount_tiyin, orig_amount_tiyin, orig_currency, method,
                      category, comment, source, created_at
               FROM transactions ORDER BY id"""
        ) as cur:
            return await cur.fetchall()


async def get_setting(key, default=None):
    async with get_db() as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
    return row[0] if row else default


async def set_setting(key, value):
    async with get_db() as db:
        await db.execute(
            """INSERT INTO settings (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, str(value)),
        )
        await db.commit()


async def get_category_limit(category):
    async with get_db() as db:
        async with db.execute(
            "SELECT limit_tiyin FROM category_limits WHERE category = ?", (category,)
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else None


async def set_category_limit(category, limit_tiyin):
    async with get_db() as db:
        await db.execute(
            """INSERT INTO category_limits (category, limit_tiyin) VALUES (?, ?)
               ON CONFLICT(category) DO UPDATE SET limit_tiyin = excluded.limit_tiyin""",
            (category, limit_tiyin),
        )
        await db.commit()
