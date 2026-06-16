"""Admin edits for active tasks; all visible changes trigger refreshed graph output."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.repositories import EmployeeRepository, TaskRepository
from keyboards.inline_keyboards import admin_task_actions, deadline_offer_button, employees_keyboard, priorities_keyboard
from services.cleanup_service import CleanupService
from services.notification_service import NotificationService
from states.task_states import ManageTaskStates
from utils.constants import PRIORITIES
from utils.datetime_utils import format_deadline, now_local, parse_deadline, to_db_datetime
from utils.text_utils import task_details_text, task_display_id

router = Router(name="task_management")


async def _guard(callback: CallbackQuery, is_admin: bool) -> bool:
    if is_admin:
        return True
    await callback.answer("Bu amal faqat admin uchun.", show_alert=True)
    return False


async def _refresh_graph(task, employee_repo: EmployeeRepository, notifications: NotificationService, settings) -> None:
    employee = await employee_repo.get(task.employee_id)
    if employee:
        await notifications.send_employee_graph(employee)
        await notifications.send_employee_graph(employee, settings.admin_id, admin_view=True)


@router.callback_query(F.data.startswith("admin:detail:"))
async def admin_detail(callback: CallbackQuery, is_admin: bool, task_repo: TaskRepository, settings) -> None:
    if not await _guard(callback, is_admin):
        return
    task = await task_repo.get(int(callback.data.rsplit(":", 1)[1]))
    if not task:
        await callback.answer("Topshiriq topilmadi.", show_alert=True)
        return
    await callback.message.answer(task_details_text(task, settings.timezone), reply_markup=admin_task_actions(task.id))
    await callback.answer()


@router.callback_query(F.data.startswith("manage:deadline:"))
async def manage_deadline_start(callback: CallbackQuery, state: FSMContext, is_admin: bool, cleanup: CleanupService) -> None:
    if not await _guard(callback, is_admin):
        return
    task_id = int(callback.data.rsplit(":", 1)[1])
    await state.set_state(ManageTaskStates.waiting_deadline)
    await state.update_data(task_id=task_id)
    sent = await callback.message.answer("Yangi deadline kiriting.\nFormat: DD.MM.YYYY HH:MM")
    await cleanup.remember(sent.chat.id, sent.message_id, "manage")
    await callback.answer()


@router.message(ManageTaskStates.waiting_deadline)
async def manage_deadline_save(message: Message, state: FSMContext, is_admin: bool, task_repo: TaskRepository, employee_repo: EmployeeRepository, notifications: NotificationService, settings, cleanup: CleanupService) -> None:
    if not is_admin:
        return
    try:
        deadline = parse_deadline(message.text or "", settings.timezone)
    except ValueError:
        await message.answer("Deadline noto‘g‘ri. Format: DD.MM.YYYY HH:MM")
        return
    if deadline <= now_local(settings.timezone):
        await message.answer("Deadline kelajakdagi vaqt bo‘lishi kerak.")
        return
    task_id = (await state.get_data())["task_id"]
    await task_repo.approve_deadline(task_id, to_db_datetime(deadline), message.from_user.id, edited=True)
    task = await task_repo.get(task_id)
    await state.clear()
    await cleanup.cleanup(message.chat.id, "manage")
    await message.answer(f"✅ Deadline yangilandi: {format_deadline(deadline, settings.timezone)}")
    if task:
        await notifications.safe_message(task.employee_telegram_user_id, f"📅 {task_display_id(task.task_number)} topshiriq uchun yangi deadline: {format_deadline(deadline, settings.timezone)}")
        await _refresh_graph(task, employee_repo, notifications, settings)


@router.callback_query(F.data.startswith("manage:priority:"))
async def manage_priority_start(callback: CallbackQuery, is_admin: bool) -> None:
    if not await _guard(callback, is_admin):
        return
    task_id = int(callback.data.rsplit(":", 1)[1])
    await callback.message.answer("Yangi priority ni tanlang:", reply_markup=priorities_keyboard(f"managepriority:{task_id}"))
    await callback.answer()


@router.callback_query(F.data.startswith("managepriority:"))
async def manage_priority_save(callback: CallbackQuery, is_admin: bool, task_repo: TaskRepository, employee_repo: EmployeeRepository, notifications: NotificationService, settings) -> None:
    if not await _guard(callback, is_admin):
        return
    _, task_id, priority = callback.data.split(":")
    if priority not in PRIORITIES:
        await callback.answer("Priority noto‘g‘ri.", show_alert=True)
        return
    task = await task_repo.update_fields(int(task_id), callback.from_user.id, priority=priority, priority_label=PRIORITIES[priority]["label"])
    if task:
        await callback.message.answer(f"✅ Priority {priority} ga o‘zgartirildi.")
        await notifications.safe_message(task.employee_telegram_user_id, f"🚦 {task_display_id(task.task_number)} topshiriq priority si {priority} ga o‘zgartirildi.")
        await _refresh_graph(task, employee_repo, notifications, settings)
    await callback.answer()


@router.callback_query(F.data.startswith("manage:title:"))
async def manage_title_start(callback: CallbackQuery, state: FSMContext, is_admin: bool, cleanup: CleanupService) -> None:
    if not await _guard(callback, is_admin):
        return
    await state.set_state(ManageTaskStates.waiting_title)
    await state.update_data(task_id=int(callback.data.rsplit(":", 1)[1]))
    sent = await callback.message.answer("Yangi to‘liq topshiriq matnini yuboring.")
    await cleanup.remember(sent.chat.id, sent.message_id, "manage")
    await callback.answer()


@router.message(ManageTaskStates.waiting_title)
async def manage_title_save(message: Message, state: FSMContext, is_admin: bool, task_repo: TaskRepository, cleanup: CleanupService) -> None:
    if not is_admin:
        return
    title = (message.text or "").strip()
    if len(title) < 3:
        await message.answer("Topshiriq matni juda qisqa.")
        return
    task_id = (await state.get_data())["task_id"]
    await task_repo.update_fields(task_id, message.from_user.id, title=title)
    await state.clear()
    await cleanup.cleanup(message.chat.id, "manage")
    await message.answer("✅ Topshiriq matni yangilandi.")


@router.callback_query(F.data.startswith("manage:short:"))
async def manage_short_start(callback: CallbackQuery, state: FSMContext, is_admin: bool, cleanup: CleanupService) -> None:
    if not await _guard(callback, is_admin):
        return
    await state.set_state(ManageTaskStates.waiting_short_title)
    await state.update_data(task_id=int(callback.data.rsplit(":", 1)[1]))
    sent = await callback.message.answer("Grafik uchun yangi qisqa nomni yuboring.")
    await cleanup.remember(sent.chat.id, sent.message_id, "manage")
    await callback.answer()


@router.message(ManageTaskStates.waiting_short_title)
async def manage_short_save(message: Message, state: FSMContext, is_admin: bool, task_repo: TaskRepository, employee_repo: EmployeeRepository, notifications: NotificationService, settings, cleanup: CleanupService) -> None:
    if not is_admin:
        return
    short_title = (message.text or "").strip()
    if len(short_title) < 2:
        await message.answer("Qisqa nom kiriting.")
        return
    task_id = (await state.get_data())["task_id"]
    task = await task_repo.update_fields(task_id, message.from_user.id, short_title=short_title)
    await state.clear()
    await cleanup.cleanup(message.chat.id, "manage")
    await message.answer("✅ Grafikdagi qisqa nom yangilandi.")
    if task and task.status in ("ACTIVE", "OVERDUE"):
        await _refresh_graph(task, employee_repo, notifications, settings)


@router.callback_query(F.data.startswith("manage:employee:"))
async def manage_employee_start(callback: CallbackQuery, is_admin: bool, employee_repo: EmployeeRepository) -> None:
    if not await _guard(callback, is_admin):
        return
    task_id = int(callback.data.rsplit(":", 1)[1])
    await callback.message.answer("Yangi xodimni tanlang:", reply_markup=employees_keyboard(await employee_repo.list_all(), f"reassign:{task_id}", include_cancel=False))
    await callback.answer()


@router.callback_query(F.data.startswith("reassign:"))
async def manage_employee_save(callback: CallbackQuery, is_admin: bool, task_repo: TaskRepository, employee_repo: EmployeeRepository, notifications: NotificationService, settings) -> None:
    if not await _guard(callback, is_admin):
        return
    _, task_id_raw, employee_id_raw = callback.data.split(":")
    task = await task_repo.get(int(task_id_raw))
    new_employee = await employee_repo.get(int(employee_id_raw))
    old_employee = await employee_repo.get(task.employee_id) if task else None
    if not task or not new_employee or not new_employee.telegram_user_id:
        await callback.answer("Tanlangan xodim uchun Telegram user ID biriktirilmagan.", show_alert=True)
        return
    updated = await task_repo.update_fields(task.id, callback.from_user.id, employee_id=new_employee.id)
    await callback.message.answer(f"✅ Topshiriq {new_employee.role_name} xodimiga biriktirildi.")
    if updated:
        if updated.status == "WAITING_EMPLOYEE_DEADLINE":
            await callback.bot.send_message(
                new_employee.telegram_user_id,
                f"📌 Sizga yangi topshiriq biriktirildi\n\n🆔 Topshiriq ID: {task_display_id(updated.task_number)}\n📝 Topshiriq: {updated.title}\n\nDeadline sana va vaqtini DD.MM.YYYY HH:MM formatida taklif qiling.",
                reply_markup=deadline_offer_button(updated.id),
            )
        else:
            await notifications.safe_message(new_employee.telegram_user_id, f"📌 Sizga {task_display_id(updated.task_number)} topshiriq biriktirildi: {updated.title}")
        if old_employee:
            await notifications.send_employee_graph(old_employee)
            await notifications.send_employee_graph(old_employee, settings.admin_id, admin_view=True)
        await _refresh_graph(updated, employee_repo, notifications, settings)
    await callback.answer()


@router.callback_query(F.data.startswith("manage:history:"))
async def manage_history(callback: CallbackQuery, is_admin: bool, task_repo: TaskRepository) -> None:
    if not await _guard(callback, is_admin):
        return
    task_id = int(callback.data.rsplit(":", 1)[1])
    rows = await task_repo.history(task_id)
    lines = ["📜 Topshiriq tarixi:"]
    for row in rows[-30:]:
        lines.append(f"• {row['action_type']}: {row['old_value'] or '—'} → {row['new_value'] or '—'}")
    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data.startswith("manage:cancel:"))
async def manage_cancel(callback: CallbackQuery, is_admin: bool, task_repo: TaskRepository, employee_repo: EmployeeRepository, notifications: NotificationService, settings) -> None:
    if not await _guard(callback, is_admin):
        return
    task = await task_repo.cancel(int(callback.data.rsplit(":", 1)[1]), callback.from_user.id)
    if not task:
        await callback.answer("Topshiriqni bekor qilib bo‘lmaydi.", show_alert=True)
        return
    await callback.message.answer("✅ Topshiriq bekor qilindi.")
    await notifications.safe_message(task.employee_telegram_user_id, f"❌ {task_display_id(task.task_number)} topshiriq admin tomonidan bekor qilindi.")
    await _refresh_graph(task, employee_repo, notifications, settings)
    await callback.answer()
