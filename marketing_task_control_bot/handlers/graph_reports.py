"""Image report entry points for admin and employees."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from database.repositories import EmployeeRepository
from keyboards.inline_keyboards import employees_keyboard
from services.notification_service import NotificationService

router = Router(name="graph_reports")


@router.message(F.text == "📊 Ish vazifalari grafigi")
async def admin_graph_menu(message: Message, is_admin: bool, employee_repo: EmployeeRepository) -> None:
    if not is_admin:
        await message.answer("Bu amal faqat admin uchun.")
        return
    employees = await employee_repo.list_all()
    await message.answer("Qaysi xodimning ish vazifalari grafigini ko‘rmoqchisiz?", reply_markup=employees_keyboard(employees, "graph:employee", include_cancel=False, back_callback="menu:back"))


@router.callback_query(F.data.startswith("graph:employee:"))
async def send_admin_graph(callback: CallbackQuery, is_admin: bool, employee_repo: EmployeeRepository, notifications: NotificationService) -> None:
    if not is_admin:
        await callback.answer("Bu amal faqat admin uchun.", show_alert=True)
        return
    employee = await employee_repo.get(int(callback.data.rsplit(":", 1)[1]))
    if not employee:
        await callback.answer("Xodim topilmadi.", show_alert=True)
        return
    await notifications.send_employee_graph(employee, callback.from_user.id, admin_view=True)
    await callback.answer()


@router.message(F.text.in_({"📊 Mening ish vazifalarim grafigi", "🔄 Grafikni yangilash"}))
async def employee_graph(message: Message, is_admin: bool, employee, notifications: NotificationService) -> None:
    if is_admin:
        await message.answer("Admin uchun grafik bo‘limi: 📊 Ish vazifalari grafigi")
        return
    await notifications.send_employee_graph(employee)
