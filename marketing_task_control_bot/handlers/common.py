"""Start and common navigation handlers."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.repositories import UserRepository
from keyboards.admin_keyboards import admin_main_menu
from keyboards.employee_keyboards import employee_main_menu
from services.cleanup_service import CleanupService
from services.notification_service import NotificationService

router = Router(name="common")


@router.message(CommandStart())
async def start_handler(message: Message, is_admin: bool, employee, user_repo: UserRepository, notifications: NotificationService) -> None:
    full_name = message.from_user.full_name if message.from_user else "User"
    if is_admin:
        await user_repo.upsert(message.from_user.id, full_name, "ADMIN", True)
        await message.answer("Marketing Task Control Bot admin paneliga xush kelibsiz.", reply_markup=admin_main_menu())
        return
    await user_repo.upsert(message.from_user.id, full_name, employee.role_name, False)
    await notifications.send_employee_graph(employee)
    await message.answer(f"Assalomu alaykum, {employee.role_name}. Menyudan foydalaning.", reply_markup=employee_main_menu())


@router.callback_query(F.data == "workflow:cancel")
async def cancel_workflow(callback: CallbackQuery, state: FSMContext, cleanup: CleanupService, is_admin: bool) -> None:
    await state.clear()
    for workflow in ("task_create", "settings", "deadline", "manage"):
        await cleanup.cleanup(callback.message.chat.id, workflow)
    menu = admin_main_menu() if is_admin else employee_main_menu()
    await callback.message.answer("Jarayon bekor qilindi.", reply_markup=menu)
    await callback.answer()


@router.callback_query(F.data == "workflow:back")
async def workflow_back(callback: CallbackQuery, state: FSMContext, cleanup: CleanupService, is_admin: bool) -> None:
    await state.clear()
    for workflow in ("task_create", "settings", "deadline", "manage"):
        await cleanup.cleanup(callback.message.chat.id, workflow)
    menu = admin_main_menu() if is_admin else employee_main_menu()
    await callback.message.answer("Asosiy menyuga qaytildi.", reply_markup=menu)
    await callback.answer()


@router.callback_query(F.data == "menu:back")
async def back_to_menu(callback: CallbackQuery, is_admin: bool) -> None:
    menu = admin_main_menu() if is_admin else employee_main_menu()
    await callback.message.answer("Asosiy menyu.", reply_markup=menu)
    await callback.answer()
