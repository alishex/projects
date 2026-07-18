import logging

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

import app.config as cfg
from app.keyboards import poll_keyboard
from app.services.menu_service import get_tomorrow_menu
from app.services.report_service import build_owner_report
import app.database as db

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Asia/Tashkent")

POLL_JOB_ID = "send_daily_poll"
REPORT_JOB_ID = "send_owner_report"

_scheduler: AsyncIOScheduler | None = None


def _parse_hhmm(value: str, fallback: tuple[int, int]) -> tuple[int, int]:
    try:
        h, m = value.strip().split(":")
        h, m = int(h), int(m)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except (ValueError, AttributeError):
        pass
    return fallback


async def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    global _scheduler
    scheduler = AsyncIOScheduler(
        timezone=TZ,
        # Default misfire_grace_time apscheduler'da 1 soniya — restart/deploy
        # yoki event loop bir zum band bo'lishi kunlik jobni butunlay
        # o'tkazib yubormasligi uchun kengroq qildik.
        job_defaults={"misfire_grace_time": 3600, "coalesce": True},
    )

    settings = await db.get_settings()
    poll_h, poll_m = _parse_hhmm((settings or {}).get("poll_time") or cfg.DEFAULT_POLL_TIME, (17, 0))
    rep_h, rep_m = _parse_hhmm((settings or {}).get("report_time") or cfg.DEFAULT_REPORT_TIME, (18, 0))

    scheduler.add_job(
        send_daily_poll, CronTrigger(hour=poll_h, minute=poll_m, timezone=TZ),
        args=[bot], id=POLL_JOB_ID, replace_existing=True,
    )
    scheduler.add_job(
        send_owner_report, CronTrigger(hour=rep_h, minute=rep_m, timezone=TZ),
        args=[bot], id=REPORT_JOB_ID, replace_existing=True,
    )
    logger.info("Scheduler tayyor: %02d:%02d so'rov, %02d:%02d hisobot", poll_h, poll_m, rep_h, rep_m)
    _scheduler = scheduler
    return scheduler


async def reschedule_poll_time(hh: int, mm: int):
    """Owner panel orqali so'rov yuborish vaqtini qayta ishga tushirmasdan o'zgartiradi."""
    if _scheduler is None:
        raise RuntimeError("Scheduler hali ishga tushmagan.")
    _scheduler.reschedule_job(POLL_JOB_ID, trigger=CronTrigger(hour=hh, minute=mm, timezone=TZ))
    await db.update_schedule_times(poll_time=f"{hh:02d}:{mm:02d}")
    logger.info("So'rov yuborish vaqti %02d:%02d ga o'zgartirildi.", hh, mm)


async def reschedule_report_time(hh: int, mm: int):
    """Owner panel orqali hisobot vaqtini qayta ishga tushirmasdan o'zgartiradi."""
    if _scheduler is None:
        raise RuntimeError("Scheduler hali ishga tushmagan.")
    _scheduler.reschedule_job(REPORT_JOB_ID, trigger=CronTrigger(hour=hh, minute=mm, timezone=TZ))
    await db.update_schedule_times(report_time=f"{hh:02d}:{mm:02d}")
    logger.info("Hisobot vaqti %02d:%02d ga o'zgartirildi.", hh, mm)


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

    # cfg.DEPARTMENTS (DB'dan) bo'yicha aylanamiz — shunda owner panelda
    # qo'shilgan/o'chirilgan/o'zgartirilgan bo'limlar ham restart shart
    # bo'lmasdan darhol to'g'ri hisobga olinadi. Bitta admin bir nechta
    # bo'limga mas'ul bo'lsa ham, har bir bo'limga alohida so'rov boradi.
    sent = 0
    for dept in cfg.DEPARTMENTS:
        if dept.get("fixed_meal1") is not None and dept.get("fixed_meal2") is not None:
            # Doimiy sonli bo'lim (masalan Boshliqlar) — soni hech qachon
            # o'zgarmaydi, shuning uchun so'rov yuborilmaydi, to'g'ridan-to'g'ri
            # tasdiqlangan buyurtma sifatida yoziladi (hisobotda ko'rinishi uchun).
            try:
                await db.upsert_order(
                    date_str=target_date,
                    dept_key=dept["key"],
                    admin_id=0,
                    meal1_count=dept["fixed_meal1"],
                    meal2_count=dept["fixed_meal2"],
                    confirmed=True,
                )
                sent += 1
            except Exception as e:
                logger.error(f"send_daily_poll: {dept['key']} doimiy buyurtmani yozib bo'lmadi — {e}")
            continue

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

    logger.info(f"send_daily_poll: {sent}/{len(cfg.DEPARTMENTS)} bo'limga yuborildi, sana={target_date}")


async def send_owner_report(bot: Bot):
    if not cfg.OWNER_IDS:
        logger.error("send_owner_report: owner belgilanmagan — hisobot yuborilmadi")
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

        # Barcha ownerlar teng huquqli — biriga yuborilmasa ham qolganlari
        # o'z hisobotini olishi kerak, shuning uchun alohida try/except.
        sent = 0
        for owner_id in cfg.OWNER_IDS:
            try:
                await bot.send_message(owner_id, report, parse_mode="HTML")
                sent += 1
            except Exception as e:
                logger.warning(f"send_owner_report: owner {owner_id} ga yuborib bo'lmadi — {e}")

        logger.info(f"send_owner_report: {sent}/{len(cfg.OWNER_IDS)} ownerga yuborildi, sana={target_date}")
    except Exception as e:
        logger.error(f"send_owner_report: xatolik — {e}", exc_info=True)
