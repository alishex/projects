"""Reject every unassigned user before a handler can expose internal content."""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from database.repositories import EmployeeRepository
from utils.constants import UNAUTHORIZED_MESSAGE


class AuthMiddleware(BaseMiddleware):
    def __init__(self, employee_repo: EmployeeRepository, admin_id: int):
        self.employee_repo = employee_repo
        self.admin_id = admin_id

    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)
        if user.id == self.admin_id:
            data["is_admin"] = True
            data["employee"] = None
            return await handler(event, data)
        employee = await self.employee_repo.get_by_user_id(user.id)
        if employee:
            data["is_admin"] = False
            data["employee"] = employee
            return await handler(event, data)
        if isinstance(event, CallbackQuery):
            await event.answer(UNAUTHORIZED_MESSAGE, show_alert=True)
        elif isinstance(event, Message):
            await event.answer(UNAUTHORIZED_MESSAGE)
        return None
