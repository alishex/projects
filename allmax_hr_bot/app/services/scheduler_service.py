from __future__ import annotations

import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from app.config import settings
from app.database import db
from app.utils.validators import h
from app.services.clockster_service import sync_all_clockster_attendance

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone=settings.timezone)


def parse_interview_input(text: str) -> tuple[datetime, str]:
    # Format: 2026-05-20 15:00 | Chilonzor filiali
    if "|" in text:
        dt_part, location = text.split("|", 1)
    else:
        dt_part, location = text, settings.default_shop_address
    dt = datetime.strptime(dt_part.strip(), "%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=settings.tz), location.strip() or settings.default_shop_address


async def send_followup(bot: Bot, interview_id: int) -> None:
    interview = db.get_interview(interview_id)
    if not interview or interview.get("followup_status") != "pending":
        return
    candidate = db.get_candidate(int(interview["candidate_id"]))
    if not candidate:
        return
    await bot.send_message(
        int(candidate["telegram_id"]),
        "Assalomu alaykum. Intervyu qanday o‘tdi? Sizni ishga qabul qilishdimi yoki hali javob kutyapsizmi?",
    )
    db.update_interview(interview_id, followup_status="asked")
    db.log(None, "followup_sent", "interview", interview_id)


def schedule_followup(bot: Bot, interview_id: int, run_at: datetime) -> None:
    job_id = f"followup_{interview_id}"
    try:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        scheduler.add_job(send_followup, "date", id=job_id, run_date=run_at, args=[bot, interview_id], replace_existing=True)
    except Exception as exc:
        logger.warning("Followup schedule failed: %s", exc)


def schedule_existing_followups(bot: Bot) -> None:
    for row in db.due_followups():
        try:
            run_at = datetime.strptime(row["followup_due_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=settings.tz)
            if run_at < datetime.now(settings.tz):
                run_at = datetime.now(settings.tz) + timedelta(seconds=10)
            schedule_followup(bot, int(row["id"]), run_at)
        except Exception as exc:
            logger.warning("Existing followup not scheduled: %s", exc)


async def run_clockster_sync() -> None:
    if not settings.clockster_ready:
        return
    try:
        result = await sync_all_clockster_attendance()
        logger.info("Clockster sync result: %s", result)
    except Exception as exc:
        logger.exception("Clockster scheduled sync failed: %s", exc)


def schedule_clockster_sync() -> None:
    if not settings.clockster_ready:
        logger.info("Clockster sync disabled or token missing.")
        return
    minutes = max(int(settings.clockster_sync_interval_minutes or 15), 5)
    try:
        scheduler.add_job(run_clockster_sync, "interval", minutes=minutes, id="clockster_sync", replace_existing=True)
    except Exception as exc:
        logger.warning("Clockster schedule failed: %s", exc)


def start_scheduler(bot: Bot) -> None:
    if not scheduler.running:
        scheduler.start()
    schedule_existing_followups(bot)
    schedule_clockster_sync()
