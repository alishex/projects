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

_scheduler: AsyncIOScheduler | None = None

MENU_JOB_ID = "send_menu_1330"
REPORT_JOB_ID = "final_report_2200"


def _parse_hhmm(value: str, fallback: tuple[int, int]) -> tuple[int, int]:
    try:
        h, m = value.strip().split(":")
        h, m = int(h), int(m)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except (ValueError, AttributeError):
        pass
    return fallback


async def send_tomorrow_menu(bot: Bot):
    """Barcha foydalanuvchilarga ertangi menyu yuboriladi (vaqti sozlanadigan)."""
    menu = await get_tomorrow_menu()
    if not menu:
        log.warning("Ertangi menyu topilmadi.")
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
                    f"⚠️ Quyidagi xodimlar botga ulanmaganlar (menyu xabari yuborilmadi):\n{names}"
                )
            except Exception as e:
                log.warning("Adminga 'ulanmaganlar' xabarini yubora olmadim: %s", e)

    log.info("Ertangi menyu yuborildi: %d foydalanuvchiga.", len(users) - len(not_started))


async def send_daily_final_report(bot: Bot):
    """Bugungi yakuniy hisobot adminga va guruhga (vaqti sozlanadigan)."""
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

    log.info("Yakuniy hisobot yuborildi.")


async def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    global _scheduler
    scheduler = AsyncIOScheduler(timezone=TZ)

    settings = await db.get_settings()
    menu_h, menu_m = _parse_hhmm((settings or {}).get("menu_send_time") or "13:30", (13, 30))
    rep_h, rep_m = _parse_hhmm((settings or {}).get("report_time") or "22:00", (22, 0))

    scheduler.add_job(
        send_tomorrow_menu,
        CronTrigger(hour=menu_h, minute=menu_m, timezone=TZ),
        kwargs={"bot": bot},
        id=MENU_JOB_ID,
        replace_existing=True,
    )

    scheduler.add_job(
        send_daily_final_report,
        CronTrigger(hour=rep_h, minute=rep_m, timezone=TZ),
        kwargs={"bot": bot},
        id=REPORT_JOB_ID,
        replace_existing=True,
    )

    log.info("Scheduler tayyor: %02d:%02d menyu, %02d:%02d hisobot (TZ: %s)",
              menu_h, menu_m, rep_h, rep_m, cfg.TIMEZONE)
    _scheduler = scheduler
    return scheduler


async def reschedule_menu_time(hh: int, mm: int):
    """Admin panel orqali menyu yuborish vaqtini qayta ishga tushirmasdan o'zgartiradi."""
    if _scheduler is None:
        raise RuntimeError("Scheduler hali ishga tushmagan.")
    _scheduler.reschedule_job(MENU_JOB_ID, trigger=CronTrigger(hour=hh, minute=mm, timezone=TZ))
    await db.update_schedule_times(menu_send_time=f"{hh:02d}:{mm:02d}")
    log.info("Menyu yuborish vaqti %02d:%02d ga o'zgartirildi.", hh, mm)


async def reschedule_report_time(hh: int, mm: int):
    """Admin panel orqali yakuniy hisobot vaqtini qayta ishga tushirmasdan o'zgartiradi."""
    if _scheduler is None:
        raise RuntimeError("Scheduler hali ishga tushmagan.")
    _scheduler.reschedule_job(REPORT_JOB_ID, trigger=CronTrigger(hour=hh, minute=mm, timezone=TZ))
    await db.update_schedule_times(report_time=f"{hh:02d}:{mm:02d}")
    log.info("Yakuniy hisobot vaqti %02d:%02d ga o'zgartirildi.", hh, mm)
