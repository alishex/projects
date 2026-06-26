from datetime import date
import app.database as db


async def get_today_order(telegram_id: int) -> dict | None:
    return await db.get_order(date.today().isoformat(), telegram_id)


async def get_tomorrow_order(telegram_id: int) -> dict | None:
    from datetime import timedelta
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    return await db.get_order(tomorrow, telegram_id)


async def save_temp_order(telegram_id: int, meal_1_status: str | None,
                           meal_2_status: str | None):
    from datetime import timedelta
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    await db.upsert_order(tomorrow, telegram_id, meal_1_status, meal_2_status, is_confirmed=0)


async def confirm_tomorrow_order(telegram_id: int, meal_1_status: str, meal_2_status: str):
    from datetime import timedelta
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    await db.confirm_order(tomorrow, telegram_id, meal_1_status, meal_2_status)


async def all_confirmed_tomorrow() -> bool:
    from datetime import timedelta
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    users = await db.get_all_active_employees()
    orders = await db.get_orders_for_date(tomorrow)
    confirmed_ids = {o["telegram_id"] for o in orders if o["is_confirmed"] == 1}
    return all(u["telegram_id"] in confirmed_ids for u in users)
