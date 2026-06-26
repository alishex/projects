import logging
from datetime import timedelta
from app.utils import today as _today

import pytz
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import app.database as db
import app.config as cfg
from app.services.menu_service import get_tomorrow_menu, format_menu_text
from app.services.report_service import build_order_report, build_final_report
from app.keyboards import meal_selection_keyboard
from app.handlers.callbacks import UserState

log = logging.getLogger(__name__)
TZ = pytz.timezone(cfg.TIMEZONE)


async def send_tomorrow_menu(bot: Bot):
    """17:30 — Barcha foydalanuvchilarga ertangi menyu yuboriladi."""
    menu = await get_tomorrow_menu()
    if not menu:
        log.warning("13:30: Ertangi menyu topilmadi.")
        return

    users = await db.get_all_active_users()
    text = format_menu_text(menu)
    kb = meal_selection_keyboard()

    not_started = []
    for user in users:
        tid = user["telegram_id"]
        if not user["has_started"]:
            not_started.append(user)
            continue
        try:
            await bot.send_message(tid, text, reply_markup=kb)
        except TelegramForbiddenError:
            log.warning("User %s botni bloklagan yoki boshmagan.", tid)
            await db.add_or_update_user(tid, user["full_name"], user["username"],
                                         user["role"], has_started=0)
            not_started.append(user)
        except TelegramBadRequest as e:
            log.warning("User %s ga xabar yubora olmadim: %s", tid, e)
            not_started.append(user)
        except Exception as e:
            log.exception("User %s ga xabar yuborishda xato: %s", tid, e)

    # Adminga bot boshlamaganlar haqida xabar
    if not_started:
        settings = await db.get_settings()
        admin_id = settings.get("admin_id") if settings else cfg.SUPER_ADMIN_ID
        if admin_id:
            names = "\n".join(
                f"- {u.get('full_name', 'Nomaʼlum')} (ID: {u['telegram_id']})"
                for u in not_started
            )
            try:
                await bot.send_message(
                    admin_id,
                    f"⚠️ Quyidagi xodimlar botga ulanmaganlar (13:30 xabar yuborilamdi):\n{names}"
                )
            except Exception:
                pass

    log.info("13:30: %d foydalanuvchiga menyu yuborildi.", len(users) - len(not_started))


async def send_daily_final_report(bot: Bot):
    """22:00 — Bugungi yakuniy hisobot adminga va guruhga."""
    today = _today().isoformat()
    report = await build_final_report(today)

    settings = await db.get_settings()
    admin_id = settings.get("admin_id") if settings else cfg.SUPER_ADMIN_ID
    group_id = settings.get("group_id") if settings else None

    if admin_id:
        try:
            await bot.send_message(admin_id, report)
        except Exception as e:
            log.warning("Admin ga yakuniy hisobot yubora olmadim: %s", e)

    if group_id:
        try:
            await bot.send_message(group_id, report)
        except Exception as e:
            log.warning("Guruhga yakuniy hisobot yubora olmadim: %s", e)

    log.info("22:00: Yakuniy hisobot yuborildi.")


async def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TZ)

    scheduler.add_job(
        send_tomorrow_menu,
        CronTrigger(hour=13, minute=30, timezone=TZ),
        kwargs={"bot": bot},
        id="send_menu_1330",
        replace_existing=True,
    )

    scheduler.add_job(
        send_daily_final_report,
        CronTrigger(hour=22, minute=0, timezone=TZ),
        kwargs={"bot": bot},
        id="final_report_2200",
        replace_existing=True,
    )

    log.info("Scheduler tayyor: 13:30 menyu, 22:00 hisobot (TZ: %s)", cfg.TIMEZONE)
    return scheduler
