from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database import db
from app.keyboards.user_keyboards import language_keyboard, main_keyboard, draft_keyboard
from app.utils.texts import UZ_WELCOME, RU_WELCOME

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Iltimos, tilni tanlang / Пожалуйста, выберите язык:", reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def choose_language(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    lang = (callback.data or "lang:uz").split(":", 1)[1]
    await state.update_data(language=lang)
    draft = db.get_draft(callback.from_user.id)
    text = UZ_WELCOME if lang == "uz" else RU_WELCOME
    await callback.message.answer(text, reply_markup=main_keyboard(lang))
    if draft and int(draft.get("field_index") or 0) > 0:
        await callback.message.answer("Sizda yakunlanmagan ariza bor. Davom ettirasizmi yoki yangisini boshlaysizmi?", reply_markup=draft_keyboard())


@router.callback_query(F.data == "draft:new")
async def draft_new(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    db.delete_draft(callback.from_user.id)
    data = await state.get_data()
    await callback.message.answer("Yangi ariza boshlash uchun bo‘sh ish o‘rinlaridan lavozim tanlang.", reply_markup=main_keyboard(data.get("language", "uz")))
