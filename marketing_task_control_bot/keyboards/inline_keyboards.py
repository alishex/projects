"""Reusable inline keyboards."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Employee, Task
from utils.constants import PRIORITIES
from utils.text_utils import task_display_id


def employees_keyboard(employees: list[Employee], prefix: str, include_cancel: bool = True, back_callback: str | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for employee in employees:
        suffix = " ✅" if employee.is_assigned else " ⚪"
        builder.button(text=f"{employee.role_name}{suffix}", callback_data=f"{prefix}:{employee.id}")
    builder.adjust(1)
    if back_callback:
        builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data=back_callback))
    if include_cancel:
        builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="workflow:cancel"))
    return builder.as_markup()


def priorities_keyboard(prefix: str = "create_priority") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, data in PRIORITIES.items():
        builder.row(InlineKeyboardButton(text=data["button"], callback_data=f"{prefix}:{code}"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="workflow:back"))
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="workflow:cancel"))
    return builder.as_markup()


def send_task_confirmation() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yuborish", callback_data="create:send")],
        [InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="create:edit")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="workflow:cancel")],
    ])


def deadline_offer_button(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Deadline taklif qilish", callback_data=f"proposal:start:{task_id}")]
    ])


def admin_deadline_approval(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ma’qul", callback_data=f"deadline:approve:{task_id}"),
         InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"deadline:edit:{task_id}")]
    ])


def tasks_keyboard(tasks: list[Task], prefix: str, back_callback: str = "menu:back") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for task in tasks:
        icon = PRIORITIES[task.priority]["icon"]
        builder.row(InlineKeyboardButton(text=f"{icon} {task_display_id(task.task_number)} {task.short_title}", callback_data=f"{prefix}:{task.id}"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data=back_callback))
    return builder.as_markup()


def employee_task_actions(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tugatdim", callback_data=f"complete:ask:{task_id}")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="employee:tasks")],
    ])


def employee_complete_confirmation(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, tugatdim", callback_data=f"complete:confirm:{task_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"employee:detail:{task_id}")],
    ])


def admin_filters() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Barcha faol topshiriqlar", callback_data="adminfilter:all")],
        [InlineKeyboardButton(text="Xodim bo‘yicha", callback_data="adminfilter:employees"), InlineKeyboardButton(text="Priority bo‘yicha", callback_data="adminfilter:priorities")],
        [InlineKeyboardButton(text="Deadline yaqinlashganlar", callback_data="adminfilter:near"), InlineKeyboardButton(text="Kechikkanlar", callback_data="adminfilter:overdue")],
    ])


def priority_filter_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{data['icon']} {code}", callback_data=f"adminfilter:priority:{code}") for code, data in PRIORITIES.items()],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="adminfilter:home")],
    ])


def admin_task_actions(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Deadline ni o‘zgartirish", callback_data=f"manage:deadline:{task_id}"),
         InlineKeyboardButton(text="🚦 Priority ni o‘zgartirish", callback_data=f"manage:priority:{task_id}")],
        [InlineKeyboardButton(text="📝 Matnni tahrirlash", callback_data=f"manage:title:{task_id}"),
         InlineKeyboardButton(text="✂️ Qisqa nomni tahrirlash", callback_data=f"manage:short:{task_id}")],
        [InlineKeyboardButton(text="👤 Boshqa xodimga berish", callback_data=f"manage:employee:{task_id}"),
         InlineKeyboardButton(text="📜 Tarix", callback_data=f"manage:history:{task_id}")],
        [InlineKeyboardButton(text="❌ Topshiriqni bekor qilish", callback_data=f"manage:cancel:{task_id}")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="adminfilter:all")],
    ])
