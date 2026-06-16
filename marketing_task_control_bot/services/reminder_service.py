"""Persistent deadline reminders and automatic overdue transitions."""
from __future__ import annotations

import logging
from datetime import timedelta

from database.repositories import EmployeeRepository, ReminderRepository, TaskRepository
from services.notification_service import NotificationService
from services.task_service import TaskService
from utils.datetime_utils import format_deadline, from_db_datetime, now_local, to_db_datetime
from utils.text_utils import task_display_id

logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self, task_repo: TaskRepository, employee_repo: EmployeeRepository, reminder_repo: ReminderRepository,
                 task_service: TaskService, notifications: NotificationService):
        self.task_repo = task_repo
        self.employee_repo = employee_repo
        self.reminder_repo = reminder_repo
        self.task_service = task_service
        self.notifications = notifications
        self.timezone = task_service.timezone

    async def check_deadlines(self) -> None:
        try:
            now = now_local(self.timezone)
            tasks = await self.task_service.active_all()
            for task in tasks:
                deadline = from_db_datetime(task.final_deadline, self.timezone)
                if not deadline:
                    continue
                employee = await self.employee_repo.get(task.employee_id)
                if not employee:
                    continue
                remaining = deadline - now
                if task.status == "ACTIVE" and remaining.total_seconds() <= 0:
                    updated = await self.task_repo.mark_overdue(task.id)
                    if updated and not await self.reminder_repo.is_sent(task.id, "OVERDUE"):
                        text = (
                            "⚠️ Deadline o‘tib ketdi\n\n"
                            f"🆔 Topshiriq ID: {task_display_id(task.task_number)}\n"
                            f"👤 Xodim: {employee.role_name}\n"
                            f"📝 Topshiriq: {task.short_title}\n"
                            f"📅 Deadline: {format_deadline(deadline, self.timezone)}\n\n"
                            "Topshiriq hali bajarilmagan."
                        )
                        employee_ok = await self.notifications.safe_message(employee.telegram_user_id, text)
                        admin_ok = await self.notifications.safe_message(self.notifications.admin_id, text)
                        if employee_ok or admin_ok:
                            await self.reminder_repo.mark_sent(task.id, "OVERDUE", to_db_datetime(deadline) or "")
                        await self.notifications.send_employee_graph(employee)
                        await self.notifications.send_employee_graph(employee, self.notifications.admin_id, admin_view=True)
                    continue
                if task.status != "ACTIVE" or remaining.total_seconds() <= 0:
                    continue
                threshold = None
                targets_admin = False
                if remaining <= timedelta(hours=1):
                    threshold, targets_admin = "H1", True
                elif remaining <= timedelta(hours=3):
                    threshold = "H3"
                elif remaining <= timedelta(hours=24):
                    threshold = "H24"
                if threshold and not await self.reminder_repo.is_sent(task.id, threshold):
                    text = (
                        "⏰ Deadline yaqinlashmoqda\n\n"
                        f"🆔 Topshiriq ID: {task_display_id(task.task_number)}\n"
                        f"📝 Topshiriq: {task.short_title}\n"
                        f"📅 Deadline: {format_deadline(deadline, self.timezone)}\n\n"
                        "Topshiriqni o‘z vaqtida yakunlashni unutmang."
                    )
                    sent = await self.notifications.safe_message(employee.telegram_user_id, text)
                    if targets_admin:
                        sent = await self.notifications.safe_message(self.notifications.admin_id, text) or sent
                    if sent:
                        await self.reminder_repo.mark_sent(task.id, threshold, to_db_datetime(deadline) or "")
        except Exception:
            logger.exception("Deadline tekshirishda xatolik yuz berdi.")
