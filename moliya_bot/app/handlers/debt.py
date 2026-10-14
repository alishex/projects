from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import OWNER_ID
from app.keyboards import debt_menu_kb, main_menu
from app.services import debt_service
from app.services.fx_service import parse_amount
from app.utils import fmt_sum, fmt_usd

router = Router()
router.message.filter(F.from_user.id == OWNER_ID)
router.callback_query.filter(F.from_user.id == OWNER_ID)


class DebtForm(StatesGroup):
    person = State()
    amount = State()
    comment = State()


def _fmt(amount_tiyin: int, currency: str) -> str:
    return fmt_usd(amount_tiyin) if currency == "USD" else fmt_sum(amount_tiyin)


@router.message(F.text == "🤝 Қарз")
async def debt_menu(message: Message):
    await message.answer("Қарз бўлими:", reply_markup=debt_menu_kb())


@router.callback_query(F.data.in_({"debt:given", "debt:taken"}))
async def debt_start(callback: CallbackQuery, state: FSMContext):
    direction = "given" if callback.data == "debt:given" else "taken"
    await state.update_data(direction=direction)
    await state.set_state(DebtForm.person)
    verb = "кимга бердингиз" if direction == "given" else "кимдан олдингиз"
    await callback.message.edit_text(f"Шахс исмини киритинг ({verb}):")
    await callback.answer()


@router.message(DebtForm.person)
async def debt_person(message: Message, state: FSMContext):
    await state.update_data(person=message.text.strip())
    await state.set_state(DebtForm.amount)
    await message.answer("Миқдорни киритинг:")


@router.message(DebtForm.amount)
async def debt_amount(message: Message, state: FSMContext):
    parsed = parse_amount(message.text)
    if parsed is None:
        await message.answer("Тушунмадим, қайта киритинг:")
        return
    amount_minor, currency = parsed
    await state.update_data(amount_minor=amount_minor, currency=currency)
    await state.set_state(DebtForm.comment)
    await message.answer("Изоҳ ёзинг (ёки /skip):")


@router.message(DebtForm.comment)
async def debt_comment(message: Message, state: FSMContext):
    comment = None if message.text.strip() == "/skip" else message.text.strip()
    data = await state.get_data()
    await debt_service.add_debt(
        direction=data["direction"],
        person=data["person"],
        amount_tiyin=data["amount_minor"],
        currency=data["currency"],
        comment=comment,
    )
    await state.clear()
    verb = "берилди" if data["direction"] == "given" else "олинди"
    amount_str = _fmt(data["amount_minor"], data["currency"])
    await message.answer(
        f"✅ Қарз қайд этилди: {data['person']} — {amount_str} ({verb})", reply_markup=main_menu()
    )


@router.callback_query(F.data == "debt:list")
async def debt_list(callback: CallbackQuery):
    debts = await debt_service.list_open_debts()
    if not debts:
        await callback.message.edit_text("Очиқ қарзлар йўқ.")
        await callback.answer()
        return

    lines = ["📋 Очиқ қарзлар:\n"]
    b = InlineKeyboardBuilder()
    for debt_id, direction, person, amount_tiyin, currency, comment in debts:
        amount_str = _fmt(amount_tiyin, currency)
        arrow = "→" if direction == "given" else "←"
        line = f"{arrow} {person}: {amount_str}"
        if comment:
            line += f" ({comment})"
        lines.append(line)
        b.button(text=f"✅ {person} ({amount_str}) тўланди", callback_data=f"debt:close:{debt_id}")
    b.adjust(1)
    await callback.message.edit_text("\n".join(lines), reply_markup=b.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("debt:close:"))
async def debt_close(callback: CallbackQuery):
    debt_id = int(callback.data.split(":")[2])
    await debt_service.close_debt(debt_id)
    await callback.answer("Қарз ёпилди ✅")
    await debt_list(callback)
