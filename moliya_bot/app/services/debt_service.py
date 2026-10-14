from app.database import get_db
from app.utils import now


async def add_debt(direction, person, amount_tiyin, currency, comment):
    async with get_db() as db:
        await db.execute(
            """INSERT INTO debts (direction, person, amount_tiyin, currency, comment, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'open', ?)""",
            (direction, person, amount_tiyin, currency, comment, now().isoformat()),
        )
        await db.commit()


async def list_open_debts():
    async with get_db() as db:
        async with db.execute(
            """SELECT id, direction, person, amount_tiyin, currency, comment
               FROM debts WHERE status = 'open' ORDER BY id"""
        ) as cur:
            return await cur.fetchall()


async def close_debt(debt_id):
    async with get_db() as db:
        await db.execute(
            "UPDATE debts SET status = 'closed', closed_at = ? WHERE id = ?",
            (now().isoformat(), debt_id),
        )
        await db.commit()
