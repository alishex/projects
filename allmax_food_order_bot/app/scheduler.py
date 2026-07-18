import logging

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from app.config import DEPARTMENTS, OWNER_IDS
from app.keyboards import poll_keyboard
from app.services.menu_service import get_tomorrow_menu
from app.services.report_service import build_owner_report
import app.database as db

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Asia/Tashkent")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(
        timezone=TZ,
        # Default misfire_grace_time apscheduler'da 1 soniya — restart/deploy
        # yoki event loop bir zum band bo'lishi kunlik jobni butunlay
        # o'tkazib yubormasligi uchun kengroq qildik.
        job_defaults={"misfire_grace_time": 3600, "coalesce": True},
    )
    scheduler.add_job(send_daily_poll,   CronTrigger(hour=17, minute=0, timezone=TZ), args=[bot])
    scheduler.add_job(send_owner_report, CronTrigger(hour=18, minute=0, timezone=TZ), args=[bot])
    return scheduler


async def send_daily_poll(bot: Bot):
    try:
        menu = await get_tomorrow_menu()
    except Exception:
        logger.error("send_daily_poll: menyuni olishda xato", exc_info=True)
        return

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

    # DEPARTMENTS bo'yicha (admin_id bo'yicha emas) aylanamiz — shunda bitta
    # admin bir nechta bo'limga mas'ul bo'lsa ham, har bir bo'limga alohida
    # so'rov boradi (aks holda ular bitta admin ID'da "qo'shilib" ketib,
    # bo'limlardan biri so'rovsiz qolib ketardi).
    sent = 0
    for dept in DEPARTMENTS:
        admin_id = dept.get("admin_id")
        if admin_id is None:
            continue
        try:
            await bot.send_message(
                admin_id,
                text,
                parse_mode="HTML",
                # O'rinbosar belgilangan bo'limlarda admin bugungi so'rovni
                # o'rinbosarga yuborish tugmasini ham ko'radi.
                reply_markup=poll_keyboard(target_date, dept["key"], show_delegate=bool(dept.get("deputy_id")))
            )
            sent += 1
        except Exception as e:
            logger.warning(f"send_daily_poll: {dept['key']} (admin {admin_id}) ga yuborib bo'lmadi — {e}")

    logger.info(f"send_daily_poll: {sent}/{len(DEPARTMENTS)} bo'limga yuborildi, sana={target_date}")


async def send_owner_report(bot: Bot):
    if not OWNER_IDS:
        logger.error("send_owner_report: OWNER_ID_1/OWNER_ID_2 sozlanmagan — hisobot yuborilmadi")
        return

    try:
        menu = await get_tomorrow_menu()
        if not menu:
            logger.warning("send_owner_report: menu topilmadi")
            return

        target_date = menu["date_str"]
        orders = await db.get_orders_for_date(target_date)

        report = build_owner_report(
            date_display=menu["date_display"],
            meal1_name=menu["meal_1"],
            meal2_name=menu["meal_2"],
            orders=orders
        )

        # Ikkala owner ham teng huquqli — biriga yuborilmasa ham ikkinchisi
        # o'z hisobotini olishi kerak, shuning uchun alohida try/except.
        sent = 0
        for owner_id in OWNER_IDS:
            try:
                await bot.send_message(owner_id, report, parse_mode="HTML")
                sent += 1
            except Exception as e:
                logger.warning(f"send_owner_report: owner {owner_id} ga yuborib bo'lmadi — {e}")

        logger.info(f"send_owner_report: {sent}/{len(OWNER_IDS)} ownerga yuborildi, sana={target_date}")
    except Exception as e:
        logger.error(f"send_owner_report: xatolik — {e}", exc_info=True)
