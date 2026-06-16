from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database import db
from app.keyboards.user_keyboards import vacancy_keyboard, start_application_keyboard
from app.services.dynamic_service import brief_for_vacancy
from app.utils.validators import h, chunk_text

router = Router()


@router.message(F.text.in_({"💼 Bo‘sh ish o‘rinlari", "💼 Вакансии"}))
async def vacancies(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "uz")
    items = db.list_vacancies(status="active")
    if not items:
        text = "Hozircha faol bo‘sh ish o‘rinlari mavjud emas." if lang == "uz" else "Сейчас активных вакансий нет."
        await message.answer(text)
        return
    text = "Quyidagi lavozimlardan birini tanlang:" if lang == "uz" else "Выберите вакансию:"
    await message.answer(text, reply_markup=vacancy_keyboard(items, lang))


@router.callback_query(F.data.startswith("vac:"))
async def vacancy_detail(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    vacancy_id = int((callback.data or "vac:0").split(":")[1])
    vacancy = db.get_vacancy(vacancy_id)
    if not vacancy or vacancy.get("status") != "active":
        await callback.message.answer("Ushbu vakansiya hozir faol emas.")
        return
    data = await state.get_data()
    lang = data.get("language", "uz")
    await state.update_data(position=vacancy.get("name_uz"), vacancy_id=vacancy_id)
    # All database/admin text is escaped before it enters Telegram HTML parse mode.
    safe = {k: h(v) if isinstance(v, str) else v for k, v in vacancy.items()}
    text = brief_for_vacancy(safe, lang)
    chunks = chunk_text(text, 3800)
    for part in chunks[:-1]:
        await callback.message.answer(part)
    await callback.message.answer(chunks[-1], reply_markup=start_application_keyboard(vacancy_id, lang))
