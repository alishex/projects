"""Employee task actions and two-sided deadline agreement workflow."""
from __future__ import annotations

from datetime import datetime
import re

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.repositories import EmployeeRepository, TaskRepository
from keyboards.inline_keyboards import admin_deadline_approval, employee_complete_confirmation, employee_task_actions, tasks_keyboard
from services.cleanup_service import CleanupService
from services.notification_service import NotificationService
from services.task_service import TaskService
from states.task_states import DeadlineEditStates, DeadlineProposalStates
from utils.datetime_utils import format_deadline, now_local, parse_deadline, to_db_datetime, from_db_datetime
from utils.text_utils import priority_text, task_details_text, task_display_id

router = Router(name="employee")
DEADLINE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}$")
INVALID_DEADLINE = (
    "Deadline noto‘g‘ri formatda yuborildi.\n\n"
    "Iltimos, quyidagi formatdan foydalaning:\n"
    "DD.MM.YYYY HH:MM\n\nMasalan:\n29.05.2026 18:00"
)


async def _submit_proposal(message: Message, task, state: FSMContext, task_repo: TaskRepository, settings, cleanup: CleanupService) -> bool:
    try:
        deadline = parse_deadline(message.text or "", settings.timezone)
    except ValueError:
        sent = await message.answer(INVALID_DEADLINE)
        await cleanup.remember(sent.chat.id, sent.message_id, "deadline")
        return False
    if deadline <= now_local(settings.timezone):
        sent = await message.answer("Deadline hozirgi vaqtdan keyin bo‘lishi kerak.\n\n" + INVALID_DEADLINE)
        await cleanup.remember(sent.chat.id, sent.message_id, "deadline")
        return False
    await task_repo.set_proposed_deadline(task.id, to_db_datetime(deadline), message.from_user.id)
    await state.clear()
    await cleanup.cleanup(message.chat.id, "deadline")
    await message.answer(f"✅ Taklif qilingan deadline adminga yuborildi: {format_deadline(deadline, settings.timezone)}")
    admin_text = (
        "⏳ Xodim topshiriq uchun deadline taklif qildi\n\n"
        f"🆔 Topshiriq ID: {task_display_id(task.task_number)}\n"
        f"👤 Xodim: {task.employee_role}\n"
        f"📝 Topshiriq: {task.title}\n"
        f"🚦 Muhimlilik: {priority_text(task.priority)}\n"
        f"📅 Taklif qilingan deadline: {format_deadline(deadline, settings.timezone)}\n\n"
        "Shu muddatga rozimisiz?"
    )
    await message.bot.send_message(settings.admin_id, admin_text, reply_markup=admin_deadline_approval(task.id))
    return True


@router.callback_query(F.data.startswith("proposal:start:"))
async def start_proposal(callback: CallbackQuery, state: FSMContext, is_admin: bool, employee, task_repo: TaskRepository, cleanup: CleanupService) -> None:
    if is_admin or not employee:
        await callback.answer("Bu amal xodim uchun.", show_alert=True)
        return
    task_id = int(callback.data.rsplit(":", 1)[1])
    task = await task_repo.get(task_id)
    if not task or task.employee_id != employee.id or task.status != "WAITING_EMPLOYEE_DEADLINE":
        await callback.answer("Topshiriq deadline qabul qilish holatida emas.", show_alert=True)
        return
    await state.set_state(DeadlineProposalStates.waiting_deadline)
    await state.update_data(task_id=task_id)
    sent = await callback.message.answer("Deadline sana va vaqtini yuboring.\nFormat: DD.MM.YYYY HH:MM")
    await cleanup.remember(sent.chat.id, sent.message_id, "deadline")
    await callback.answer()


@router.message(DeadlineProposalStates.waiting_deadline)
async def receive_proposal(message: Message, state: FSMContext, is_admin: bool, employee, task_repo: TaskRepository, settings, cleanup: CleanupService) -> None:
    if is_admin or not employee:
        return
    data = await state.get_data()
    task = await task_repo.get(data.get("task_id", 0))
    if not task or task.employee_id != employee.id or task.status != "WAITING_EMPLOYEE_DEADLINE":
        await state.clear()
        await message.answer("Bu topshiriq uchun deadline qabul qilish yakunlangan.")
        return
    await _submit_proposal(message, task, state, task_repo, settings, cleanup)


@router.message(StateFilter(None), F.text.regexp(r"^\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}$"))
async def receive_direct_proposal(message: Message, state: FSMContext, is_admin: bool, employee, task_repo: TaskRepository, settings, cleanup: CleanupService) -> None:
    if is_admin or not employee:
        return
    pending = await task_repo.list_pending_for_employee_user(message.from_user.id)
    if len(pending) == 1:
        await _submit_proposal(message, pending[0], state, task_repo, settings, cleanup)
    elif len(pending) > 1:
        await message.answer("Bir nechta yangi topshiriq mavjud. Deadline yuborishdan oldin topshiriq xabaridagi tugmani bosing.")


@router.callback_query(F.data.startswith("deadline:approve:"))
async def approve_deadline(callback: CallbackQuery, is_admin: bool, task_repo: TaskRepository, employee_repo: EmployeeRepository, notifications: NotificationService, settings) -> None:
    if not is_admin:
        await callback.answer("Bu amal faqat admin uchun.", show_alert=True)
        return
    task_id = int(callback.data.rsplit(":", 1)[1])
    task = await task_repo.get(task_id)
    if not task or task.status != "WAITING_ADMIN_APPROVAL" or not task.proposed_deadline:
        await callback.answer("Tasdiqlash uchun topshiriq topilmadi.", show_alert=True)
        return
    await task_repo.approve_deadline(task.id, task.proposed_deadline, callback.from_user.id)
    employee = await employee_repo.get(task.employee_id)
    final_text = (
        "✅ Deadline tasdiqlandi\n\n"
        f"🆔 Topshiriq ID: {task_display_id(task.task_number)}\n"
        f"📅 Yakuniy deadline: {format_deadline(task.proposed_deadline, settings.timezone)}\n\n"
        "Topshiriqni shu vaqtgacha yakunlashingiz kerak."
    )
    await notifications.safe_message(employee.telegram_user_id if employee else None, final_text)
    if employee:
        await notifications.send_employee_graph(employee)
        await notifications.send_employee_graph(employee, settings.admin_id, admin_view=True)
    await callback.message.answer("✅ Deadline ma’qullandi.")
    await callback.answer()


@router.callback_query(F.data.startswith("deadline:edit:"))
async def begin_admin_deadline_edit(callback: CallbackQuery, state: FSMContext, is_admin: bool, cleanup: CleanupService) -> None:
    if not is_admin:
        await callback.answer("Bu amal faqat admin uchun.", show_alert=True)
        return
    task_id = int(callback.data.rsplit(":", 1)[1])
    await state.set_state(DeadlineEditStates.waiting_deadline)
    await state.update_data(task_id=task_id)
    sent = await callback.message.answer("Bu topshiriq uchun yangi deadline kiriting.\n\nFormat:\nDD.MM.YYYY HH:MM")
    await cleanup.remember(sent.chat.id, sent.message_id, "deadline")
    await callback.answer()


@router.message(DeadlineEditStates.waiting_deadline)
async def admin_set_deadline(message: Message, state: FSMContext, is_admin: bool, task_repo: TaskRepository, employee_repo: EmployeeRepository, notifications: NotificationService, settings, cleanup: CleanupService) -> None:
    if not is_admin:
        return
    try:
        deadline = parse_deadline(message.text or "", settings.timezone)
    except ValueError:
        sent = await message.answer(INVALID_DEADLINE)
        await cleanup.remember(sent.chat.id, sent.message_id, "deadline")
        return
    if deadline <= now_local(settings.timezone):
        sent = await message.answer("Yangi deadline kelajakdagi vaqt bo‘lishi kerak.")
        await cleanup.remember(sent.chat.id, sent.message_id, "deadline")
        return
    task_id = (await state.get_data())["task_id"]
    task = await task_repo.get(task_id)
    if not task:
        await message.answer("Topshiriq topilmadi.")
        await state.clear()
        return
    await task_repo.approve_deadline(task_id, to_db_datetime(deadline), message.from_user.id, edited=True)
    employee_record = await employee_repo.get(task.employee_id)
    await state.clear()
    await cleanup.cleanup(message.chat.id, "deadline")
    text = (
        "📅 Sizga yangi deadline belgilandi\n\n"
        f"🆔 Topshiriq ID: {task_display_id(task.task_number)}\n"
        f"📝 Topshiriq: {task.title}\n"
        f"📅 Yakuniy deadline: {format_deadline(deadline, settings.timezone)}\n\n"
        "Topshiriqni shu vaqtgacha yakunlashingiz kerak."
    )
    await notifications.safe_message(employee_record.telegram_user_id if employee_record else None, text)
    if employee_record:
        await notifications.send_employee_graph(employee_record)
        await notifications.send_employee_graph(employee_record, settings.admin_id, admin_view=True)
    await message.answer("✅ Yangi deadline belgilandi.")


@router.message(F.text == "📋 Topshiriqni tanlash")
async def list_employee_tasks(message: Message, is_admin: bool, employee, task_service: TaskService) -> None:
    if is_admin:
        return
    tasks = await task_service.active_for_employee(employee.id)
    if not tasks:
        await message.answer("Faol topshiriqlar mavjud emas.")
        return
    await message.answer("Topshiriqni tanlang.", reply_markup=tasks_keyboard(tasks, "employee:detail"))


@router.callback_query(F.data == "employee:tasks")
async def callback_employee_tasks(callback: CallbackQuery, is_admin: bool, employee, task_service: TaskService) -> None:
    if is_admin:
        await callback.answer("Bu amal xodim uchun.", show_alert=True)
        return
    tasks = await task_service.active_for_employee(employee.id)
    await callback.message.answer("Topshiriqni tanlang.", reply_markup=tasks_keyboard(tasks, "employee:detail"))
    await callback.answer()


@router.callback_query(F.data.startswith("employee:detail:"))
async def employee_task_detail(callback: CallbackQuery, is_admin: bool, employee, task_repo: TaskRepository, settings) -> None:
    if is_admin:
        await callback.answer("Bu amal xodim uchun.", show_alert=True)
        return
    task = await task_repo.get(int(callback.data.rsplit(":", 1)[1]))
    if not task or task.employee_id != employee.id or task.status not in ("ACTIVE", "OVERDUE"):
        await callback.answer("Topshiriq mavjud emas.", show_alert=True)
        return
    await callback.message.answer(task_details_text(task, settings.timezone), reply_markup=employee_task_actions(task.id))
    await callback.answer()


@router.callback_query(F.data.startswith("complete:ask:"))
async def ask_complete(callback: CallbackQuery, is_admin: bool, employee, task_repo: TaskRepository) -> None:
    if is_admin:
        await callback.answer("Bu amal xodim uchun.", show_alert=True)
        return
    task = await task_repo.get(int(callback.data.rsplit(":", 1)[1]))
    if not task or task.employee_id != employee.id or task.status not in ("ACTIVE", "OVERDUE"):
        await callback.answer("Topshiriqni tugatib bo‘lmaydi.", show_alert=True)
        return
    await callback.message.answer("Ushbu topshiriqni yakunlangan deb belgilaysizmi?", reply_markup=employee_complete_confirmation(task.id))
    await callback.answer()


@router.callback_query(F.data.startswith("complete:confirm:"))
async def confirm_complete(callback: CallbackQuery, is_admin: bool, employee, task_repo: TaskRepository, notifications: NotificationService, settings) -> None:
    if is_admin:
        await callback.answer("Bu amal xodim uchun.", show_alert=True)
        return
    task_id = int(callback.data.rsplit(":", 1)[1])
    before = await task_repo.get(task_id)
    if not before or before.employee_id != employee.id:
        await callback.answer("Topshiriq mavjud emas.", show_alert=True)
        return
    completed = await task_repo.complete(task_id, callback.from_user.id)
    if not completed:
        await callback.answer("Topshiriq oldin yakunlangan yoki bekor qilingan.", show_alert=True)
        return
    now = now_local(settings.timezone)
    deadline = from_db_datetime(before.final_deadline, settings.timezone)
    conclusion = "Topshiriq muddatidan oldin bajarildi." if deadline and now <= deadline else "Topshiriq deadline dan keyin bajarildi."
    admin_text = (
        "✅ Topshiriq bajarildi\n\n"
        f"🆔 Topshiriq ID: {task_display_id(before.task_number)}\n"
        f"👤 Xodim: {employee.role_name}\n"
        f"📝 Topshiriq: {before.title}\n"
        f"🚦 Muhimlilik: {priority_text(before.priority)}\n"
        f"📅 Deadline: {format_deadline(before.final_deadline, settings.timezone)}\n"
        f"🏁 Tugatilgan vaqt: {now.strftime('%d.%m.%Y %H:%M')}\n\n{conclusion}"
    )
    await callback.message.answer("✅ Topshiriq yakunlangan deb belgilandi.")
    await notifications.safe_message(settings.admin_id, admin_text)
    await notifications.send_employee_graph(employee)
    await notifications.send_employee_graph(employee, settings.admin_id, admin_view=True)
    await callback.answer()


@router.message(F.text == "⏰ Deadline yaqinlashganlar")
async def employee_near(message: Message, is_admin: bool, employee, task_service: TaskService) -> None:
    if is_admin:
        tasks = await task_service.near_deadline()
        if not tasks:
            await message.answer("24 soat ichida yaqinlashayotgan deadline mavjud emas.")
            return
        await message.answer("⏰ 24 soat ichidagi deadline lar:", reply_markup=tasks_keyboard(tasks, "admin:detail"))
        return
    tasks = await task_service.near_deadline(employee.id)
    if not tasks:
        await message.answer("24 soat ichida yaqinlashayotgan deadline mavjud emas.")
        return
    await message.answer("⏰ Deadline yaqinlashgan topshiriqlar:", reply_markup=tasks_keyboard(tasks, "employee:detail"))


@router.message(F.text == "🏁 Tugatilganlar")
async def employee_completed(message: Message, is_admin: bool, employee, task_service: TaskService) -> None:
    if is_admin:
        return
    tasks = await task_service.completed_for_employee(employee.id)
    if not tasks:
        await message.answer("Tugatilgan topshiriqlar mavjud emas.")
        return
    lines = ["🏁 Tugatilgan topshiriqlar:"] + [f"• {task_display_id(t.task_number)} {t.short_title}" for t in tasks[:30]]
    await message.answer("\n".join(lines))
