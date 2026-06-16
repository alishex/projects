"""Admin list, filter and archive entry points."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.repositories import EmployeeRepository, TaskRepository
from keyboards.inline_keyboards import admin_filters, employees_keyboard, priority_filter_keyboard, tasks_keyboard
from services.task_service import TaskService
from utils.datetime_utils import from_db_datetime, now_local
from utils.text_utils import task_display_id

router = Router(name="admin")


async def _admin_only(event, is_admin: bool) -> bool:
    if is_admin:
        return True
    if isinstance(event, CallbackQuery):
        await event.answer("Bu amal faqat admin uchun.", show_alert=True)
    else:
        await event.answer("Bu amal faqat admin uchun.")
    return False


async def _send_task_list(message: Message, heading: str, tasks, prefix: str = "admin:detail") -> None:
    if not tasks:
        await message.answer(f"{heading}\n\nTopshiriqlar mavjud emas.")
        return
    await message.answer(heading, reply_markup=tasks_keyboard(tasks, prefix, "adminfilter:home"))


@router.message(F.text == "📋 Faol topshiriqlar")
async def active_tasks_home(message: Message, is_admin: bool) -> None:
    if not await _admin_only(message, is_admin):
        return
    await message.answer("📋 Faol topshiriqlar filtri:", reply_markup=admin_filters())


@router.callback_query(F.data == "adminfilter:home")
async def active_filters_callback(callback: CallbackQuery, is_admin: bool) -> None:
    if not await _admin_only(callback, is_admin):
        return
    await callback.message.answer("📋 Faol topshiriqlar filtri:", reply_markup=admin_filters())
    await callback.answer()


@router.callback_query(F.data == "adminfilter:all")
async def all_active(callback: CallbackQuery, is_admin: bool, task_service: TaskService) -> None:
    if not await _admin_only(callback, is_admin):
        return
    await _send_task_list(callback.message, "📋 Barcha faol topshiriqlar:", await task_service.active_all())
    await callback.answer()


@router.callback_query(F.data == "adminfilter:near")
async def near_active(callback: CallbackQuery, is_admin: bool, task_service: TaskService) -> None:
    if not await _admin_only(callback, is_admin):
        return
    await _send_task_list(callback.message, "⏰ 24 soat ichidagi deadline lar:", await task_service.near_deadline())
    await callback.answer()


@router.callback_query(F.data == "adminfilter:overdue")
async def overdue_active(callback: CallbackQuery, is_admin: bool, task_service: TaskService) -> None:
    if not await _admin_only(callback, is_admin):
        return
    tasks = [task for task in await task_service.active_all() if task.status == "OVERDUE"]
    await _send_task_list(callback.message, "⚠️ Kechikkan topshiriqlar:", tasks)
    await callback.answer()


@router.callback_query(F.data == "adminfilter:employees")
async def select_filter_employee(callback: CallbackQuery, is_admin: bool, employee_repo: EmployeeRepository) -> None:
    if not await _admin_only(callback, is_admin):
        return
    await callback.message.answer("Xodimni tanlang:", reply_markup=employees_keyboard(await employee_repo.list_all(), "adminfilter:employee", include_cancel=False, back_callback="adminfilter:home"))
    await callback.answer()


@router.callback_query(F.data.startswith("adminfilter:employee:"))
async def filter_by_employee(callback: CallbackQuery, is_admin: bool, task_service: TaskService, employee_repo: EmployeeRepository) -> None:
    if not await _admin_only(callback, is_admin):
        return
    employee = await employee_repo.get(int(callback.data.rsplit(":", 1)[1]))
    if not employee:
        await callback.answer("Xodim topilmadi.", show_alert=True)
        return
    await _send_task_list(callback.message, f"📋 {employee.role_name} — faol topshiriqlar:", await task_service.active_for_employee(employee.id))
    await callback.answer()


@router.callback_query(F.data == "adminfilter:priorities")
async def select_filter_priority(callback: CallbackQuery, is_admin: bool) -> None:
    if not await _admin_only(callback, is_admin):
        return
    await callback.message.answer("Priority ni tanlang:", reply_markup=priority_filter_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("adminfilter:priority:"))
async def filter_by_priority(callback: CallbackQuery, is_admin: bool, task_service: TaskService) -> None:
    if not await _admin_only(callback, is_admin):
        return
    priority = callback.data.rsplit(":", 1)[1]
    tasks = [task for task in await task_service.active_all() if task.priority == priority]
    await _send_task_list(callback.message, f"📋 {priority} priority topshiriqlari:", tasks)
    await callback.answer()


@router.message(F.text == "⏰ Deadline yaqinlashganlar")
async def admin_near(message: Message, is_admin: bool, task_service: TaskService) -> None:
    if not await _admin_only(message, is_admin):
        return
    await _send_task_list(message, "⏰ 24 soat ichidagi deadline lar:", await task_service.near_deadline())


@router.message(F.text == "⚠️ Kechikkan topshiriqlar")
async def admin_overdue(message: Message, is_admin: bool, task_service: TaskService) -> None:
    if not await _admin_only(message, is_admin):
        return
    tasks = [task for task in await task_service.active_all() if task.status == "OVERDUE"]
    await _send_task_list(message, "⚠️ Kechikkan topshiriqlar:", tasks)


@router.message(F.text == "🏁 Tugatilgan topshiriqlar")
async def archive_home(message: Message, is_admin: bool) -> None:
    if not await _admin_only(message, is_admin):
        return
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Barchasi", callback_data="archive:all")],
        [InlineKeyboardButton(text="Xodim bo‘yicha", callback_data="archive:employees")],
        [InlineKeyboardButton(text="Muddatidan oldin", callback_data="archive:ontime"), InlineKeyboardButton(text="Kech tugatilgan", callback_data="archive:late")],
    ])
    await message.answer("🏁 Tugatilgan topshiriqlar arxivi:", reply_markup=markup)


async def _archive_text(tasks, settings, label: str) -> str:
    lines = [label]
    if not tasks:
        return label + "\n\nTopshiriqlar mavjud emas."
    for task in tasks[:50]:
        lines.append(f"• {task_display_id(task.task_number)} · {task.employee_role} · {task.short_title}")
    return "\n".join(lines)


@router.callback_query(F.data == "archive:all")
async def archive_all(callback: CallbackQuery, is_admin: bool, task_repo: TaskRepository, settings) -> None:
    if not await _admin_only(callback, is_admin):
        return
    tasks = await task_repo.list_by_status(("COMPLETED",))
    await callback.message.answer(await _archive_text(tasks, settings, "🏁 Barcha tugatilgan topshiriqlar:"))
    await callback.answer()


@router.callback_query(F.data == "archive:employees")
async def archive_employees(callback: CallbackQuery, is_admin: bool, employee_repo: EmployeeRepository) -> None:
    if not await _admin_only(callback, is_admin):
        return
    await callback.message.answer("Xodimni tanlang:", reply_markup=employees_keyboard(await employee_repo.list_all(), "archive:employee", include_cancel=False, back_callback="menu:back"))
    await callback.answer()


@router.callback_query(F.data.startswith("archive:employee:"))
async def archive_by_employee(callback: CallbackQuery, is_admin: bool, employee_repo: EmployeeRepository, task_service: TaskService, settings) -> None:
    if not await _admin_only(callback, is_admin):
        return
    employee = await employee_repo.get(int(callback.data.rsplit(":", 1)[1]))
    tasks = await task_service.completed_for_employee(employee.id) if employee else []
    await callback.message.answer(await _archive_text(tasks, settings, f"🏁 {employee.role_name if employee else 'Xodim'} arxivi:"))
    await callback.answer()


@router.callback_query(F.data.in_({"archive:ontime", "archive:late"}))
async def archive_by_timing(callback: CallbackQuery, is_admin: bool, task_repo: TaskRepository, settings) -> None:
    if not await _admin_only(callback, is_admin):
        return
    completed = await task_repo.list_by_status(("COMPLETED",))
    wanted_ontime = callback.data == "archive:ontime"
    tasks = []
    for task in completed:
        completed_at = from_db_datetime(task.completed_at, settings.timezone)
        deadline = from_db_datetime(task.final_deadline, settings.timezone)
        is_ontime = bool(completed_at and deadline and completed_at <= deadline)
        if is_ontime == wanted_ontime:
            tasks.append(task)
    title = "🏁 Muddatidan oldin tugatilganlar:" if wanted_ontime else "🏁 Kech tugatilganlar:"
    await callback.message.answer(await _archive_text(tasks, settings, title))
    await callback.answer()
