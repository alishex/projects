from __future__ import annotations

import logging
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database import db
from app.keyboards.user_keyboards import choice_keyboard, phone_keyboard, remove_keyboard, consent_keyboard
from app.states import ResumeFlow
from app.utils.texts import CONSENT_TEXT
from app.utils.validators import normalize_phone, valid_birth_date, h
from app.services.openai_service import openai_service
from app.services.dynamic_service import regulation_text_for_vacancy

router = Router()
logger = logging.getLogger(__name__)

FIELDS = [
    {"key": "full_name", "q": "1/23. F.I.SH. ni to‘liq yozing.", "type": "text"},
    {"key": "birth_date", "q": "2/23. Tug‘ilgan sanangizni yozing. Masalan: 20.05.2001", "type": "birth"},
    {"key": "phone", "q": "3/23. Telefon raqamingizni yuboring.", "type": "phone"},
    {"key": "region", "q": "4/23. Yashash hududingizni tanlang yoki yozing.", "type": "choice", "options": ["Toshkent shahar", "Toshkent viloyati", "Samarqand", "Farg‘ona", "Andijon", "Namangan", "Boshqa"]},
    {"key": "district", "q": "5/23. Tumaningizni yozing.", "type": "text"},
    {"key": "address", "q": "6/23. Manzilingizni qisqacha yozing.", "type": "text"},
    {"key": "family_status", "q": "7/23. Oilaviy holatingiz?", "type": "choice", "options": ["Uylanmagan / Turmush qurmagan", "Oilali", "Boshqa"]},
    {"key": "is_student", "q": "8/23. Talabamisiz?", "type": "choice", "options": ["Ha", "Yo‘q"]},
    {"key": "study_form", "q": "O‘qish shaklingizni tanlang.", "type": "choice", "options": ["Kunduzgi", "Sirtqi", "Kechki", "Masofaviy"], "student_only": True},
    {"key": "education_place", "q": "Ta’lim muassasangiz nomi?", "type": "text", "student_only": True},
    {"key": "course", "q": "Nechanchi kursda o‘qiysiz?", "type": "text", "student_only": True},
    {"key": "study_time", "q": "Dars vaqtingizni yozing.", "type": "text", "student_only": True},
    {"key": "education_level", "q": "9/23. Ta’lim darajangiz?", "type": "choice", "options": ["O‘rta", "O‘rta maxsus", "Tugallanmagan oliy", "Oliy"]},
    {"key": "uzbek_level", "q": "10/23. O‘zbek tili darajangiz?", "type": "choice", "options": ["Erkin", "O‘rtacha", "Boshlang‘ich"]},
    {"key": "russian_level", "q": "11/23. Rus tili darajangiz?", "type": "choice", "options": ["Erkin", "O‘rtacha", "Boshlang‘ich", "Bilmayman"]},
    {"key": "english_level", "q": "12/23. Ingliz tili darajangiz?", "type": "choice", "options": ["Erkin", "O‘rtacha", "Boshlang‘ich", "Bilmayman"]},
    {"key": "computer_level", "q": "13/23. Kompyuter bilish darajangiz?", "type": "choice", "options": ["Yaxshi", "O‘rtacha", "Boshlang‘ich", "Bilmayman"]},
    {"key": "schedule_ready", "q": "14/23. Ish grafigiga tayyormisiz?", "type": "choice", "options": ["Ha", "Yo‘q", "Kelishib olsam bo‘ladi"]},
    {"key": "salary_expectation", "q": "15/23. Oylik kutilmangizni yozing.", "type": "text"},
    {"key": "vacancy_source", "q": "16/23. Bo‘sh ish joyi haqida qayerdan bildingiz?", "type": "choice", "options": ["Telegram", "Instagram", "OLX", "Do‘st/tanish", "Boshqa"]},
    {"key": "strong_sides", "q": "17/23. O‘zingizni 3 ta kuchli tomoningizni yozing.", "type": "text"},
    {"key": "weak_sides", "q": "18/23. Rivojlantirmoqchi bo‘lgan 1–2 tomoningizni yozing.", "type": "text"},
    {"key": "motivation", "q": "19/23. Nega aynan ALLMAXda ishlamoqchisiz?", "type": "text"},
    {"key": "possible_start_date", "q": "20/23. Qachondan ish boshlay olasiz?", "type": "text"},
    {"key": "has_experience", "q": "21/23. Oldin ishlaganmisiz?", "type": "choice", "options": ["Ha", "Yo‘q"]},
]

WORK_FIELDS = [
    ("company_name", "Kompaniya nomi"),
    ("years", "Qaysi yil oralig‘ida ishlagansiz?"),
    ("position", "Lavozimingiz"),
    ("responsibilities", "Asosiy mas’uliyatingiz"),
    ("had_subordinates", "Qo‘l ostingizda odam ishlaganmi? (Ha/Yo‘q)"),
    ("subordinates_count", "Agar ha bo‘lsa, nechta odam? Agar yo‘q bo‘lsa 0 yozing."),
    ("leaving_reason", "Nima sababdan ketgansiz?"),
    ("reference_name", "Tasdiqlovchi shaxs F.I.SH."),
    ("reference_phone", "Tasdiqlovchi shaxs telefon raqami"),
]


def _field_keyboard(field: dict):
    if field["type"] == "phone":
        return phone_keyboard()
    if field["type"] == "choice":
        return choice_keyboard(field["options"], columns=2)
    return remove_keyboard


def _skip(field: dict, answers: dict) -> bool:
    return bool(field.get("student_only") and str(answers.get("is_student", "")).lower() not in {"ha", "yes", "да"})


async def ask_field(message: Message, state: FSMContext, index: int, answers: dict) -> None:
    while index < len(FIELDS) and _skip(FIELDS[index], answers):
        index += 1
    data = await state.get_data()
    if index >= len(FIELDS):
        if answers.get("has_experience") == "Ha":
            await state.set_state(ResumeFlow.work_count)
            await message.answer("Nechta ish joyida ishlagansiz? Faqat son bilan yozing.", reply_markup=remove_keyboard)
            db.save_draft(message.chat.id, data.get("language", "uz"), data.get("position"), "work_count", index, answers, data.get("work", []))
            return
        await ask_photo(message, state, answers)
        return
    field = FIELDS[index]
    await state.set_state(ResumeFlow.filling)
    await state.update_data(field_index=index, answers=answers)
    db.save_draft(message.chat.id, data.get("language", "uz"), data.get("position"), "filling", index, answers, data.get("work", []))
    await message.answer(field["q"], reply_markup=_field_keyboard(field))


async def ask_photo(message: Message, state: FSMContext, answers: dict) -> None:
    await state.set_state(ResumeFlow.photo)
    await state.update_data(answers=answers)
    data = await state.get_data()
    db.save_draft(message.chat.id, data.get("language", "uz"), data.get("position"), "photo", len(FIELDS), answers, data.get("work", []))
    await message.answer(
        "22/23. Iltimos, rasm yuboring. Talablar: yuz aniq ko‘rinsin, filter bo‘lmasin, yaxshi yoritilgan bo‘lsin, bosh va yelka qismi ko‘rinsin.",
        reply_markup=remove_keyboard,
    )


@router.callback_query(F.data.startswith("start_app:"))
async def start_application(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    vacancy_id = int((callback.data or "start_app:0").split(":")[1])
    vacancy = db.get_vacancy(vacancy_id)
    if not vacancy or vacancy.get("status") != "active":
        await callback.message.answer("Ushbu vakansiya hozir ariza qabul qilmaydi.")
        return
    position = vacancy.get("name_uz") or ""
    data = await state.get_data()
    answers = {"position": position, "vacancy_id": vacancy_id}
    await state.update_data(position=position, vacancy_id=vacancy_id, answers=answers, work=[], user_id=callback.from_user.id)
    await callback.message.answer(f"Tanlangan lavozim: <b>{h(position)}</b>\nAnketani boshlaymiz.")
    await ask_field(callback.message, state, 0, answers)


@router.callback_query(F.data == "draft:continue")
async def draft_continue(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    draft = db.get_draft(callback.from_user.id)
    if not draft:
        await callback.message.answer("Draft topilmadi. Lavozim tanlab yangidan boshlang.")
        return
    saved_answers = draft.get("answers", {})
    vacancy = db.get_vacancy(int(saved_answers.get("vacancy_id") or 0)) or db.get_vacancy_by_name(draft.get("position"))
    vacancy_id = int(vacancy["id"]) if vacancy else None
    if vacancy_id:
        saved_answers["vacancy_id"] = vacancy_id
    await state.update_data(language=draft.get("language", "uz"), position=draft.get("position"), vacancy_id=vacancy_id, answers=saved_answers, work=draft.get("work", []))
    await callback.message.answer("Arizani davom ettiramiz.")
    await ask_field(callback.message, state, int(draft.get("field_index") or 0), draft.get("answers", {}))


@router.message(ResumeFlow.filling)
async def fill_field(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    index = int(data.get("field_index") or 0)
    answers = dict(data.get("answers") or {})
    field = FIELDS[index]
    value = ""
    if field["type"] == "phone":
        if message.contact and message.contact.phone_number:
            value = normalize_phone(message.contact.phone_number)
        else:
            value = normalize_phone(message.text)
        if len(value) < 9:
            await message.answer("Telefon raqam noto‘g‘ri. Qayta yuboring.", reply_markup=phone_keyboard())
            return
    else:
        value = (message.text or "").strip()
    if field["type"] == "birth" and not valid_birth_date(value):
        await message.answer("Tug‘ilgan sana noto‘g‘ri. Masalan: 20.05.2001")
        return
    if field["type"] == "choice" and value not in field["options"]:
        # Allow typed custom only for Boshqa-like questions, otherwise ask again.
        if "Boshqa" not in field.get("options", []):
            await message.answer("Iltimos, pastdagi tugmalardan birini tanlang.", reply_markup=_field_keyboard(field))
            return
    answers[field["key"]] = value
    await state.update_data(answers=answers)
    await ask_field(message, state, index + 1, answers)


@router.message(ResumeFlow.work_count)
async def work_count(message: Message, state: FSMContext) -> None:
    try:
        count = max(1, min(10, int((message.text or "1").strip())))
    except ValueError:
        await message.answer("Faqat son yozing. Masalan: 2")
        return
    await state.update_data(work_total=count, work_index=0, work_step=0, current_work={}, work=[])
    await state.set_state(ResumeFlow.work_detail)
    await message.answer(f"1-ish joyi: {WORK_FIELDS[0][1]}")


@router.message(ResumeFlow.work_detail)
async def work_detail(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    total = int(data.get("work_total") or 1)
    work_index = int(data.get("work_index") or 0)
    step = int(data.get("work_step") or 0)
    current = dict(data.get("current_work") or {})
    key, _ = WORK_FIELDS[step]
    current[key] = (message.text or "").strip()
    step += 1
    if step < len(WORK_FIELDS):
        await state.update_data(work_step=step, current_work=current)
        await message.answer(f"{work_index + 1}-ish joyi: {WORK_FIELDS[step][1]}")
        return
    work = list(data.get("work") or [])
    work.append(current)
    work_index += 1
    if work_index < total:
        await state.update_data(work=work, work_index=work_index, work_step=0, current_work={})
        await message.answer(f"{work_index + 1}-ish joyi: {WORK_FIELDS[0][1]}")
        return
    answers = dict(data.get("answers") or {})
    await state.update_data(work=work)
    await ask_photo(message, state, answers)


@router.message(ResumeFlow.photo, F.photo)
async def photo_received(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    answers = dict(data.get("answers") or {})
    answers["photo_file_id"] = message.photo[-1].file_id
    await state.update_data(answers=answers)
    await state.set_state(ResumeFlow.consent)
    await message.answer("23/23. Ma’lumotlarni saqlash va HR bo‘limiga yuborishga rozilik bering.", reply_markup=remove_keyboard)
    await message.answer(CONSENT_TEXT, reply_markup=consent_keyboard())


@router.message(ResumeFlow.photo)
async def photo_invalid(message: Message) -> None:
    await message.answer("Iltimos, rasmni foto formatida yuboring.")


@router.callback_query(ResumeFlow.consent, F.data.startswith("consent:"))
async def consent(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    agreed = (callback.data or "").endswith("yes")
    if not agreed:
        db.delete_draft(callback.from_user.id)
        await state.clear()
        await callback.message.answer("Rozilik berilmagani sababli anketa yuborilmadi.")
        return
    data = await state.get_data()
    answers = dict(data.get("answers") or {})
    answers["telegram_id"] = callback.from_user.id
    answers["username"] = callback.from_user.username or ""
    answers["language"] = data.get("language", "uz")
    answers["consent"] = 1
    vacancy_id = int(answers.get("vacancy_id") or data.get("vacancy_id") or 0)
    vacancy = db.get_vacancy(vacancy_id) if vacancy_id else db.get_vacancy_by_name(answers.get("position"))
    if not vacancy:
        await callback.message.answer("Vakansiya topilmadi. Admin bilan bog‘laning.")
        return
    vacancy_id = int(vacancy["id"])
    answers["vacancy_id"] = vacancy_id
    # Interview/stajirovka boshlanishida reglament versiyasi snapshot qilib qotiriladi.
    answers["regulation_version_snapshot"] = db.regulation_snapshot(vacancy_id)
    work = list(data.get("work") or [])
    cid = db.create_candidate(answers, work)
    db.delete_draft(callback.from_user.id)
    question_count = int(vacancy.get("interview_question_count") or 10)
    await callback.message.answer(f"Anketa qabul qilindi. Endi lavozim bo‘yicha {question_count} ta qisqa intervyu savoli beriladi.")
    candidate = db.get_candidate(cid) or answers
    reg = regulation_text_for_vacancy(vacancy_id, "interview", candidate.get("regulation_version_snapshot"))
    template = db.active_material(vacancy_id, "interview_template", 0, candidate.get("regulation_version_snapshot"))
    if template:
        import json
        questions = json.loads(template.get("content") or "[]")
    else:
        questions = await openai_service.generate_interview_questions(candidate.get("position") or "", reg, candidate, int(vacancy.get("interview_question_count") or 10))
    interview_id = db.create_ai_interview(cid, questions)
    await state.set_state(ResumeFlow.interview)
    await state.update_data(candidate_id=cid, ai_interview_id=interview_id, q_index=0, questions=questions)
    await callback.message.answer(f"1/{len(questions)}. {questions[0]['question']}", reply_markup=remove_keyboard)
