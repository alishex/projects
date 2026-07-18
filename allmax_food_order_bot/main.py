import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import BOT_TOKEN
from app.database import init_db, refresh_runtime_config
from app.handlers import admin, owner
from app.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main():
    try:
        await init_db()
        await refresh_runtime_config()

        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        # admin.router avval — bo'lim admin/o'rinbosarlarga xos /start filtri
        # bilan cheklangan, mos kelmasa navbatdagi routerga o'tadi. owner.router
        # o'z filtri bilan tekshiradi, ikkalasiga ham mos kelmasa oxirgi
        # fallback ("Sizda ruxsat yo'q.") owner.py ichida ishga tushadi.
        dp.include_router(admin.router)
        dp.include_router(owner.router)

        scheduler = await setup_scheduler(bot)
        scheduler.start()

        logger.info("Allmax Food Order Bot ishga tushdi")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception:
        logger.critical("Bot ishga tushmadi yoki kutilmagan xatolik bilan to'xtadi", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
