from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.database import db
from app.keyboards.user_keyboards import followup_unclear_keyboard, department_keyboard
from app.services.openai_service import openai_service
from app.services.lesson_service import ensure_lessons, send_current_lesson
from app.utils.validators import h

router = Router()


async def _handle_result(message: Message, interview_id: int, status: str) -> None:
    interview = db.get_interview(interview_id)
    if not interview:
        return
    candidate = db.get_candidate(int(interview["candidate_id"]))
    db.update_interview(interview_id, followup_classification=status, followup_status="completed")
    if status == "accepted":
        await message.answer("Tabriklaymiz! Qaysi bo‘limga qabul qilinganingizni tanlang:", reply_markup=department_keyboard(db.list_vacancies(status="active"), "fdept"))
    elif status == "rejected":
        if candidate:
            db.update_candidate(int(candidate["id"]), status="rejected")
        await message.answer("Tushunarli. Vaqtingiz uchun rahmat, kelgusi ishlaringizga omad tilaymiz!")
    elif status == "waiting":
        await message.answer("Tushunarli. Javob chiqqach botga yozishingiz mumkin. Adminlar ham bundan xabardor bo‘ladi.")
    else:
        await message.answer("Aniqlashtirib bering:", reply_markup=followup_unclear_keyboard())


@router.message()
async def followup_reply(message: Message) -> None:
    if not message.from_user:
        return
    pending = db.pending_followup_for_user(message.from_user.id)
    if not pending:
        return
    text = message.text or ""
    db.update_interview(int(pending["id"]), followup_reply=text)
    status = await openai_service.classify_followup(text)
    await _handle_result(message, int(pending["id"]), status)


@router.callback_query(F.data.startswith("fup:"))
async def followup_button(callback: CallbackQuery) -> None:
    await callback.answer()
    pending = db.pending_followup_for_user(callback.from_user.id)
    if not pending:
        await callback.message.answer("Aktiv follow-up topilmadi.")
        return
    status = (callback.data or "fup:unclear").split(":", 1)[1]
    await _handle_result(callback.message, int(pending["id"]), status)


@router.callback_query(F.data.startswith("fdept:"))
async def followup_department(callback: CallbackQuery) -> None:
    await callback.answer()
    vacancy_id = int((callback.data or "fdept:0").split(":")[1])
    vacancy = db.get_vacancy(vacancy_id)
    if not vacancy:
        await callback.message.answer("Vakansiya topilmadi.")
        return
    department = vacancy.get("name_uz") or ""
    candidate = db.get_candidate_by_telegram(callback.from_user.id)
    if not candidate:
        await callback.message.answer("Nomzod ma’lumoti topilmadi. Admin bilan bog‘laning.")
        return
    employee_id = db.create_employee(int(candidate["id"]), department)
    ensure_lessons(employee_id)
    await callback.message.answer(f"Siz <b>{h(department)}</b> bo‘limiga biriktirildingiz. 7 kunlik stajirovka boshlanadi.")
    await send_current_lesson(callback.message.bot, callback.from_user.id, employee_id)
