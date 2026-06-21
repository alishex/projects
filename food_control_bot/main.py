import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import BOT_TOKEN
from app.database import init_db
from app.handlers import admin, user, callbacks
from app.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger(__name__)


async def main():
    log.info("Bot ishga tushmoqda...")

    await init_db()
    log.info("Database va menyu tayyor.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    # Router tartibi muhim: admin → callbacks → user
    dp.include_router(admin.router)
    dp.include_router(callbacks.router)
    dp.include_router(user.router)

    scheduler = await setup_scheduler(bot)
    scheduler.start()

    try:
        log.info("Polling boshlanmoqda...")
        await dp.start_polling(bot, drop_pending_updates=True)
    finally:
        scheduler.shutdown()
        await bot.session.close()
        log.info("Bot to'xtatildi.")


if __name__ == "__main__":
    asyncio.run(main())
