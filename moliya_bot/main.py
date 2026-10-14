import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import BOT_TOKEN
from app.database import init_db
from app.handlers import start, expense, income, debt, dashboard, list_tx, report, settings, freeform

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger(__name__)


async def main():
    log.info("Молия боти ишга тушмоқда...")
    await init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Tartib muhim: aniq tugma/komandalar avval, erkin matn+ovoz (freeform) eng oxirida
    dp.include_router(start.router)
    dp.include_router(expense.router)
    dp.include_router(income.router)
    dp.include_router(debt.router)
    dp.include_router(dashboard.router)
    dp.include_router(list_tx.router)
    dp.include_router(report.router)
    dp.include_router(settings.router)
    dp.include_router(freeform.router)

    try:
        log.info("Polling бошланмоқда...")
        await dp.start_polling(bot, drop_pending_updates=True)
    finally:
        await bot.session.close()
        log.info("Бот тўхтатилди.")


if __name__ == "__main__":
    asyncio.run(main())
