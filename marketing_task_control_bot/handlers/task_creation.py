"""FSM workflow used by an admin to create a new assignment."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.repositories import EmployeeRepository, TaskRepository
from keyboards.inline_keyboards import deadline_offer_button, employees_keyboard, priorities_keyboard, send_task_confirmation
from services.cleanup_service import CleanupService
from states.task_states import CreateTaskStates
from utils.constants import PRIORITIES
from utils.text_utils import priority_text, task_display_id

router = Router(name="task_creation")


@router.message(F.text == "➕ Topshiriq berish")
async def begin_task(message: Message, state: FSMContext, is_admin: bool, employee_repo: EmployeeRepository, cleanup: CleanupService) -> None:
    if not is_admin:
        await message.answer("Bu amal faqat admin uchun.")
        return
    await state.clear()
    employees = await employee_repo.list_all()
    sent = await message.answer("Topshiriq bermoqchi bo‘lgan xodimni tanlang.", reply_markup=employees_keyboard(employees, "create:employee"))
    await cleanup.remember(sent.chat.id, sent.message_id, "task_create")


@router.callback_query(F.data.startswith("create:employee:"))
async def pick_employee(callback: CallbackQuery, state: FSMContext, is_admin: bool, employee_repo: EmployeeRepository, cleanup: CleanupService) -> None:
    if not is_admin:
        await callback.answer("Bu amal faqat admin uchun.", show_alert=True)
        return
    employee_id = int(callback.data.rsplit(":", 1)[1])
    employee = await employee_repo.get(employee_id)
    if not employee or not employee.is_assigned or not employee.telegram_user_id:
        await callback.message.answer("Bu xodim uchun Telegram user ID hali biriktirilmagan.")
        await callback.answer()
        return
    await state.update_data(employee_id=employee.id, employee_role=employee.role_name)
    await state.set_state(CreateTaskStates.waiting_title)
    sent = await callback.message.answer("Topshiriq matnini yuboring.")
    await cleanup.remember(sent.chat.id, sent.message_id, "task_create")
    await callback.answer()


@router.message(CreateTaskStates.waiting_title)
async def get_title(message: Message, state: FSMContext, cleanup: CleanupService) -> None:
    title = (message.text or "").strip()
    if len(title) < 3:
        sent = await message.answer("Topshiriq matni juda qisqa. Iltimos, aniq matn yuboring.")
        await cleanup.remember(sent.chat.id, sent.message_id, "task_create")
        return
    await state.update_data(title=title)
    await state.set_state(CreateTaskStates.waiting_short_title)
    sent = await message.answer("Grafikda ko‘rinadigan qisqa nomini yuboring.\nMasalan: Reklama banneri")
    await cleanup.remember(sent.chat.id, sent.message_id, "task_create")


@router.message(CreateTaskStates.waiting_short_title)
async def get_short_title(message: Message, state: FSMContext, cleanup: CleanupService) -> None:
    short_title = (message.text or "").strip()
    if len(short_title) < 2:
        sent = await message.answer("Qisqa nom kiriting.")
        await cleanup.remember(sent.chat.id, sent.message_id, "task_create")
        return
    await state.update_data(short_title=short_title)
    await state.set_state(CreateTaskStates.waiting_priority)
    note = "\nEslatma: grafik servis nomni ikki qatorga sig‘dirmasa avtomatik qisqartiradi." if len(short_title) > 45 else ""
    sent = await message.answer(f"Topshiriqning muhimlilik darajasini tanlang.{note}", reply_markup=priorities_keyboard())
    await cleanup.remember(sent.chat.id, sent.message_id, "task_create")


@router.callback_query(CreateTaskStates.waiting_priority, F.data.startswith("create_priority:"))
async def get_priority(callback: CallbackQuery, state: FSMContext, is_admin: bool, cleanup: CleanupService) -> None:
    if not is_admin:
        await callback.answer("Bu amal faqat admin uchun.", show_alert=True)
        return
    priority = callback.data.rsplit(":", 1)[1]
    if priority not in PRIORITIES:
        await callback.answer("Priority noto‘g‘ri.", show_alert=True)
        return
    await state.update_data(priority=priority)
    data = await state.get_data()
    await state.set_state(CreateTaskStates.waiting_confirmation)
    sent = await callback.message.answer(
        "Yangi topshiriq tayyor:\n\n"
        f"Xodim: {data['employee_role']}\n"
        f"Topshiriq: {data['title']}\n"
        f"Grafikdagi nomi: {data['short_title']}\n"
        f"Muhimlilik: {PRIORITIES[priority]['button']}\n\n"
        "Topshiriqni xodimga yuboraymi?",
        reply_markup=send_task_confirmation(),
    )
    await cleanup.remember(sent.chat.id, sent.message_id, "task_create")
    await callback.answer()


@router.callback_query(CreateTaskStates.waiting_confirmation, F.data == "create:edit")
async def edit_draft(callback: CallbackQuery, state: FSMContext, cleanup: CleanupService) -> None:
    await state.set_state(CreateTaskStates.waiting_title)
    sent = await callback.message.answer("Topshiriq matnini qaytadan yuboring.")
    await cleanup.remember(sent.chat.id, sent.message_id, "task_create")
    await callback.answer()


@router.callback_query(CreateTaskStates.waiting_confirmation, F.data == "create:send")
async def send_task(callback: CallbackQuery, state: FSMContext, is_admin: bool, task_repo: TaskRepository, employee_repo: EmployeeRepository, cleanup: CleanupService) -> None:
    if not is_admin:
        await callback.answer("Bu amal faqat admin uchun.", show_alert=True)
        return
    data = await state.get_data()
    employee = await employee_repo.get(data["employee_id"])
    if not employee or not employee.telegram_user_id:
        await callback.message.answer("Bu xodim uchun Telegram user ID hali biriktirilmagan.")
        return
    task = await task_repo.create(data["title"], data["short_title"], employee.id, callback.from_user.id, data["priority"])
    text = (
        "📌 Sizga yangi topshiriq berildi\n\n"
        f"🆔 Topshiriq ID: {task_display_id(task.task_number)}\n"
        f"📝 Topshiriq: {task.title}\n"
        f"🚦 Muhimlilik: {priority_text(task.priority)}\n\n"
        "Bu topshiriqni qachongacha yakunlay olasiz?\n\n"
        "Deadline sana va vaqtini quyidagi formatda yuboring:\n"
        "DD.MM.YYYY HH:MM\n\nMasalan:\n29.05.2026 18:00"
    )
    await callback.bot.send_message(employee.telegram_user_id, text, reply_markup=deadline_offer_button(task.id))
    await state.clear()
    await cleanup.cleanup(callback.message.chat.id, "task_create")
    await callback.message.answer(f"✅ {task_display_id(task.task_number)} topshiriq {employee.role_name} xodimiga yuborildi.")
    await callback.answer()
