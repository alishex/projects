"""Telegram notifications and report-photo delivery."""
from __future__ import annotations

import logging
from datetime import datetime

from aiogram import Bot
from aiogram.types import FSInputFile

from database.models import Employee
from services.matrix_image_service import MatrixImageService
from services.task_service import TaskService
from utils.datetime_utils import now_local

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot: Bot, task_service: TaskService, matrix_service: MatrixImageService, admin_id: int):
        self.bot = bot
        self.task_service = task_service
        self.matrix_service = matrix_service
        self.admin_id = admin_id

    async def safe_message(self, chat_id: int | None, text: str, **kwargs) -> bool:
        if not chat_id:
            return False
        try:
            await self.bot.send_message(chat_id, text, **kwargs)
            return True
        except Exception:
            logger.exception("Xabar yuborilmadi. chat_id=%s", chat_id)
            return False

    async def send_employee_graph(self, employee: Employee, chat_id: int | None = None, admin_view: bool = False) -> bool:
        target = chat_id or employee.telegram_user_id
        if not target:
            return False
        tasks = await self.task_service.active_for_employee(employee.id)
        now = now_local(self.matrix_service.timezone)
        paths = self.matrix_service.create_matrix_pages(tasks, employee.role_name, now)
        try:
            total = len(paths)
            for index, path in enumerate(paths, start=1):
                if admin_view:
                    heading = f"📊 {employee.role_name} — ish vazifalari grafigi"
                else:
                    heading = "📊 Sizning ish vazifalaringiz grafigi"
                if total > 1:
                    heading += f" {index}/{total}"
                caption = f"{heading}\nYangilangan vaqt: {now.strftime('%d.%m.%Y %H:%M')}"
                await self.bot.send_photo(target, FSInputFile(path), caption=caption)
            return True
        except Exception:
            logger.exception("Grafik yuborishda xato. employee=%s chat_id=%s", employee.id, target)
            await self.safe_message(target, "Grafikni yaratishda xatolik yuz berdi. Iltimos, qayta urinib ko‘ring.")
            return False
        finally:
            self.matrix_service.cleanup_generated_files(paths)
