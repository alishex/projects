import logging
from datetime import date, timedelta

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from app.config import ADMIN_TO_DEPT, OWNER_ID
from app.keyboards import poll_keyboard
from app.services.menu_service import get_tomorrow_menu
from app.services.report_service import build_owner_report
import app.database as db

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Asia/Tashkent")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TZ)
    scheduler.add_job(send_daily_poll,   CronTrigger(hour=17, minute=0, timezone=TZ), args=[bot])
    scheduler.add_job(send_owner_report, CronTrigger(hour=18, minute=0, timezone=TZ), args=[bot])
    return scheduler


async def send_daily_poll(bot: Bot):
    menu = await get_tomorrow_menu()
    if not menu:
        logger.warning("send_daily_poll: menu topilmadi")
        return

    target_date = menu["date_str"]
    date_display = menu["date_display"]
    meal1 = menu["meal_1"]
    meal2 = menu["meal_2"]

    text = (
        f"📋 <b>Ertangi ovqat buyurtmasi</b>\n"
        f"📅 {date_display}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🥘 Tushlik: <b>{meal1}</b>\n"
        f"🌙 Kechki: <b>{meal2}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Porsiyalar sonini kiriting 👇"
    )

    for admin_id in ADMIN_TO_DEPT:
        try:
            await bot.send_message(
                admin_id,
                text,
                parse_mode="HTML",
                reply_markup=poll_keyboard(target_date)
            )
        except Exception as e:
            logger.warning(f"send_daily_poll: admin {admin_id} ga yuborib bo'lmadi — {e}")

    logger.info(f"send_daily_poll: {len(ADMIN_TO_DEPT)} adminga yuborildi, sana={target_date}")


async def send_owner_report(bot: Bot):
    target_date = (date.today() + timedelta(days=1)).isoformat()
    menu = await get_tomorrow_menu()
    if not menu:
        logger.warning("send_owner_report: menu topilmadi")
        return

    orders = await db.get_orders_for_date(target_date)

    report = build_owner_report(
        date_display=menu["date_display"],
        meal1_name=menu["meal_1"],
        meal2_name=menu["meal_2"],
        orders=orders
    )

    try:
        await bot.send_message(OWNER_ID, report, parse_mode="HTML")
        logger.info(f"send_owner_report: ownerga yuborildi, sana={target_date}")
    except Exception as e:
        logger.error(f"send_owner_report: ownerga yuborib bo'lmadi — {e}")
