"""Admin employee-ID assignment settings."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.repositories import EmployeeRepository
from keyboards.inline_keyboards import employees_keyboard
from services.cleanup_service import CleanupService
from states.task_states import SettingsStates

router = Router(name="settings")


async def _reject_if_not_admin(event, is_admin: bool) -> bool:
    if is_admin:
        return False
    if isinstance(event, CallbackQuery):
        await event.answer("Bu amal faqat admin uchun.", show_alert=True)
    else:
        await event.answer("Bu amal faqat admin uchun.")
    return True


@router.message(F.text.in_({"👥 Xodimlar", "⚙️ Sozlamalar"}))
async def show_employees(message: Message, is_admin: bool, employee_repo: EmployeeRepository) -> None:
    if await _reject_if_not_admin(message, is_admin):
        return
    employees = await employee_repo.list_all()
    lines = ["👥 Xodimlar va Telegram User ID lar:", ""]
    for employee in employees:
        value = str(employee.telegram_user_id) if employee.telegram_user_id else "biriktirilmagan"
        lines.append(f"• {employee.role_name}: {value}")
    lines.append("\nO‘zgartirish uchun lavozimni tanlang.")
    await message.answer("\n".join(lines), reply_markup=employees_keyboard(employees, "settings:select"))


@router.callback_query(F.data.startswith("settings:select:"))
async def select_employee(callback: CallbackQuery, is_admin: bool, employee_repo: EmployeeRepository) -> None:
    if await _reject_if_not_admin(callback, is_admin):
        return
    employee_id = int(callback.data.rsplit(":", 1)[1])
    employee = await employee_repo.get(employee_id)
    if not employee:
        await callback.answer("Xodim topilmadi.", show_alert=True)
        return
    current = employee.telegram_user_id or "biriktirilmagan"
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 User ID biriktirish / o‘zgartirish", callback_data=f"settings:set:{employee.id}")],
        [InlineKeyboardButton(text="🗑 User ID ni olib tashlash", callback_data=f"settings:remove:{employee.id}")],
    ])
    await callback.message.answer(f"Lavozim: {employee.role_name}\nTelegram User ID: {current}", reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("settings:set:"))
async def ask_user_id(callback: CallbackQuery, state: FSMContext, is_admin: bool, employee_repo: EmployeeRepository, cleanup: CleanupService) -> None:
    if await _reject_if_not_admin(callback, is_admin):
        return
    employee_id = int(callback.data.rsplit(":", 1)[1])
    employee = await employee_repo.get(employee_id)
    if not employee:
        await callback.answer("Xodim topilmadi.", show_alert=True)
        return
    await state.set_state(SettingsStates.waiting_user_id)
    await state.update_data(employee_id=employee.id, role_name=employee.role_name)
    sent = await callback.message.answer(f"{employee.role_name} uchun yangi Telegram user ID yuboring.")
    await cleanup.remember(sent.chat.id, sent.message_id, "settings")
    await callback.answer()


@router.message(SettingsStates.waiting_user_id)
async def save_user_id(message: Message, state: FSMContext, is_admin: bool, employee_repo: EmployeeRepository, settings, cleanup: CleanupService) -> None:
    if await _reject_if_not_admin(message, is_admin):
        return
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) <= 0:
        sent = await message.answer("Telegram User ID faqat musbat raqamlardan iborat bo‘lishi kerak.")
        await cleanup.remember(sent.chat.id, sent.message_id, "settings")
        return
    data = await state.get_data()
    ok, result = await employee_repo.assign(data["employee_id"], int(text), settings.admin_id)
    if not ok:
        sent = await message.answer(result)
        await cleanup.remember(sent.chat.id, sent.message_id, "settings")
        return
    await state.clear()
    await cleanup.cleanup(message.chat.id, "settings")
    await message.answer(f"✅ Xodim muvaffaqiyatli biriktirildi\n\nLavozim: {result}\nTelegram User ID: {text}")


@router.callback_query(F.data.startswith("settings:remove:"))
async def remove_user_id(callback: CallbackQuery, is_admin: bool, employee_repo: EmployeeRepository) -> None:
    if await _reject_if_not_admin(callback, is_admin):
        return
    employee_id = int(callback.data.rsplit(":", 1)[1])
    employee = await employee_repo.get(employee_id)
    if employee and await employee_repo.unassign(employee_id):
        await callback.message.answer(f"✅ {employee.role_name} uchun Telegram User ID olib tashlandi.")
    else:
        await callback.message.answer("Xodim topilmadi.")
    await callback.answer()
