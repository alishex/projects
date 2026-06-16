from __future__ import annotations

import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.database import db
from app.handlers import start, vacancies, resume, interview, admin, dynamic_admin, followup, onboarding
from app.services.scheduler_service import start_scheduler
from app.services.dynamic_service import bootstrap_dynamic_catalog
from app.utils.logger import setup_logging


async def _run() -> None:
    setup_logging()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN .env faylida to‘ldirilmagan.")
    db.init()
    bootstrap_dynamic_catalog()
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(admin.router)
    dp.include_router(dynamic_admin.router)
    dp.include_router(onboarding.router)
    dp.include_router(start.router)
    dp.include_router(vacancies.router)
    dp.include_router(resume.router)
    dp.include_router(interview.router)
    dp.include_router(followup.router)
    start_scheduler(bot)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


def main() -> None:
    asyncio.run(_run())
