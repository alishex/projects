"""Marketing Task Control Bot entry point (long polling)."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import load_settings
from database.database import Database
from database.repositories import EmployeeRepository, ReminderRepository, TaskRepository, TemporaryMessageRepository, UserRepository
from handlers import admin, common, employee, graph_reports, settings as settings_handlers, task_creation, task_management
from middlewares.auth_middleware import AuthMiddleware
from services.cleanup_service import CleanupService
from services.matrix_image_service import MatrixImageService
from services.notification_service import NotificationService
from services.reminder_service import ReminderService
from services.task_service import TaskService
from utils.logger import setup_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = load_settings()
    setup_logging(settings.log_level, settings.logs_dir)
    logger.info("Marketing Task Control Bot ishga tushmoqda.")

    database = Database(settings.database_path)
    await database.connect()
    await database.initialize(settings.admin_id)

    employee_repo = EmployeeRepository(database)
    user_repo = UserRepository(database)
    task_repo = TaskRepository(database)
    reminder_repo = ReminderRepository(database)
    temporary_repo = TemporaryMessageRepository(database)

    bot = Bot(token=settings.bot_token)
    task_service = TaskService(task_repo, settings.timezone)
    matrix_service = MatrixImageService(settings.template_path, settings.reports_dir, settings.timezone)
    notifications = NotificationService(bot, task_service, matrix_service, settings.admin_id)
    cleanup = CleanupService(bot, temporary_repo)
    reminders = ReminderService(task_repo, employee_repo, reminder_repo, task_service, notifications)

    dispatcher = Dispatcher(storage=MemoryStorage())
    auth = AuthMiddleware(employee_repo, settings.admin_id)
    dispatcher.message.middleware(auth)
    dispatcher.callback_query.middleware(auth)

    dispatcher.include_routers(
        common.router,
        settings_handlers.router,
        task_creation.router,
        graph_reports.router,
        employee.router,
        admin.router,
        task_management.router,
    )

    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(reminders.check_deadlines, "interval", minutes=1, id="deadline_checks", replace_existing=True, max_instances=1)
    scheduler.start()
    await reminders.check_deadlines()

    try:
        await dispatcher.start_polling(
            bot,
            settings=settings,
            user_repo=user_repo,
            employee_repo=employee_repo,
            task_repo=task_repo,
            task_service=task_service,
            notifications=notifications,
            cleanup=cleanup,
        )
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        await database.close()
        logger.info("Bot to‘xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Bot operator tomonidan to‘xtatildi.")
    except Exception:
        logging.exception("Bot ishga tushmadi yoki kutilmagan xato yuz berdi.")
        raise
