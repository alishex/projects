from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from app.config import OWNER_ID
from app.keyboards import settings_kb, category_kb, main_menu
from app.services import tx_service
from app.services.fx_service import parse_amount
from app.categories import category_label
from app.utils import fmt_sum

router = Router()
router.message.filter(F.from_user.id == OWNER_ID)
router.callback_query.filter(F.from_user.id == OWNER_ID)


class SettingsForm(StatesGroup):
    rate = State()
    monthly_limit = State()
    cat_limit_pick = State()
    cat_limit_value = State()


@router.message(F.text == "⚙️ Созлаш")
async def settings_menu(message: Message):
    rate = await tx_service.get_setting("usd_rate", "12700")
    limit = int(await tx_service.get_setting("monthly_limit_tiyin", "0"))
    voice = await tx_service.get_setting("voice_enabled", "1")
    text = (
        "⚙️ <b>Жорий созламалар</b>\n"
        f"💱 Курс: 1 USD = {rate} сўм\n"
        f"📊 Ойлик лимит: {fmt_sum(limit) if limit else 'белгиланмаган'}\n"
        f"🎙 Овозли киритиш: {'ёқилган' if voice == '1' else 'ўчирилган'}"
    )
    await message.answer(text, reply_markup=settings_kb())


@router.callback_query(F.data == "set:rate")
async def ask_rate(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsForm.rate)
    await callback.message.edit_text("Янги курсни киритинг (1 USD = ? сўм):")
    await callback.answer()


@router.message(SettingsForm.rate)
async def save_rate(message: Message, state: FSMContext):
    try:
        rate = float(message.text.strip().replace(" ", ""))
    except ValueError:
        await message.answer("Рақам киритинг:")
        return
    await tx_service.set_setting("usd_rate", rate)
    await state.clear()
    await message.answer(f"✅ Курс сақланди: 1 USD = {rate} сўм", reply_markup=main_menu())


@router.callback_query(F.data == "set:monthly_limit")
async def ask_monthly_limit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsForm.monthly_limit)
    await callback.message.edit_text("Ойлик умумий харажат лимитини киритинг (мас: 5 mln):")
    await callback.answer()


@router.message(SettingsForm.monthly_limit)
async def save_monthly_limit(message: Message, state: FSMContext):
    parsed = parse_amount(message.text)
    if parsed is None:
        await message.answer("Тушунмадим, қайта киритинг:")
        return
    amount_tiyin, _ = parsed
    await tx_service.set_setting("monthly_limit_tiyin", amount_tiyin)
    await state.clear()
    await message.answer(f"✅ Ойлик лимит сақланди: {fmt_sum(amount_tiyin)}", reply_markup=main_menu())


@router.callback_query(F.data == "set:cat_limit")
async def ask_cat_limit_category(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsForm.cat_limit_pick)
    await callback.message.edit_text("Қайси категория учун лимит қўясиз?", reply_markup=category_kb("expense"))
    await callback.answer()


@router.callback_query(SettingsForm.cat_limit_pick, F.data.startswith("cat:"))
async def ask_cat_limit_value(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(SettingsForm.cat_limit_value)
    await callback.message.edit_text(f"{category_label('expense', category)} учун лимитни киритинг:")
    await callback.answer()


@router.message(SettingsForm.cat_limit_value)
async def save_cat_limit(message: Message, state: FSMContext):
    parsed = parse_amount(message.text)
    if parsed is None:
        await message.answer("Тушунмадим, қайта киритинг:")
        return
    amount_tiyin, _ = parsed
    data = await state.get_data()
    await tx_service.set_category_limit(data["category"], amount_tiyin)
    await state.clear()
    label = category_label("expense", data["category"])
    await message.answer(f"✅ {label} учун лимит сақланди: {fmt_sum(amount_tiyin)}", reply_markup=main_menu())


@router.callback_query(F.data == "set:voice_toggle")
async def toggle_voice(callback: CallbackQuery):
    current = await tx_service.get_setting("voice_enabled", "1")
    new_value = "0" if current == "1" else "1"
    await tx_service.set_setting("voice_enabled", new_value)
    await callback.answer(f"Овозли киритиш: {'ёқилди' if new_value == '1' else 'ўчирилди'}")
    await settings_menu(callback.message)
