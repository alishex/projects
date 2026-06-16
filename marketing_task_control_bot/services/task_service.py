"""Task-oriented application operations and sorted retrieval."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from database.models import Task
from database.repositories import TaskRepository
from services.priority_service import calculate_task_score, sort_tasks
from utils.datetime_utils import from_db_datetime, now_local


class TaskService:
    def __init__(self, repository: TaskRepository, timezone: ZoneInfo):
        self.repository = repository
        self.timezone = timezone

    async def active_for_employee(self, employee_id: int) -> list[Task]:
        tasks = await self.repository.list_for_employee(employee_id, ("ACTIVE", "OVERDUE"))
        return await self._score_and_sort(tasks)

    async def active_all(self) -> list[Task]:
        return await self._score_and_sort(await self.repository.list_active_all())

    async def near_deadline(self, employee_id: int | None = None, hours: int = 24) -> list[Task]:
        tasks = await self.active_for_employee(employee_id) if employee_id else await self.active_all()
        now = now_local(self.timezone)
        result = []
        for task in tasks:
            deadline = from_db_datetime(task.final_deadline, self.timezone)
            if deadline and timedelta(0) <= deadline - now <= timedelta(hours=hours):
                result.append(task)
        return result

    async def completed_for_employee(self, employee_id: int) -> list[Task]:
        return await self.repository.list_for_employee(employee_id, ("COMPLETED",))

    async def _score_and_sort(self, tasks: list[Task]) -> list[Task]:
        now = now_local(self.timezone)
        for task in tasks:
            score = calculate_task_score(task, now, self.timezone)
            task.score = score
            await self.repository.persist_score(task.id, score)
        return sort_tasks(tasks, now, self.timezone)
