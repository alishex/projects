from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from app.config import OWNER_ID
from app.keyboards import method_kb, category_kb, main_menu
from app.categories import category_label
from app.services.fx_service import parse_amount, to_uzs_tiyin
from app.services import tx_service
from app.utils import fmt_sum

router = Router()
router.message.filter(F.from_user.id == OWNER_ID)
router.callback_query.filter(F.from_user.id == OWNER_ID)


class IncomeForm(StatesGroup):
    amount = State()
    method = State()
    category = State()
    comment = State()


@router.message(F.text == "📥 Даромад")
async def start_income(message: Message, state: FSMContext):
    await state.set_state(IncomeForm.amount)
    await message.answer("Миқдорни киритинг (мас: 50000, 1.5 mln, 50 ming, $100):")


@router.message(F.text == "💼 Маош тушди")
async def quick_salary(message: Message, state: FSMContext):
    await state.update_data(category="salary", quick_salary=True)
    await state.set_state(IncomeForm.amount)
    await message.answer("Маош миқдорини киритинг:")


@router.message(IncomeForm.amount)
async def income_amount(message: Message, state: FSMContext):
    parsed = parse_amount(message.text)
    if parsed is None:
        await message.answer("Тушунмадим, қайта киритинг (мас: 50000 ёки 1.5 mln):")
        return
    amount_minor, currency = parsed
    await state.update_data(amount_minor=amount_minor, currency=currency)
    await state.set_state(IncomeForm.method)
    await message.answer("Тўлов усули:", reply_markup=method_kb())


@router.callback_query(IncomeForm.method, F.data.startswith("method:"))
async def income_method(callback: CallbackQuery, state: FSMContext):
    method = callback.data.split(":")[1]
    await state.update_data(method=method)
    data = await state.get_data()
    if data.get("quick_salary"):
        await callback.message.edit_text("Сақланмоқда...")
        await _save_income(callback.message, state, comment=None)
        await callback.answer()
        return
    await state.set_state(IncomeForm.category)
    await callback.message.edit_text("Категория танланг:", reply_markup=category_kb("income"))
    await callback.answer()


@router.callback_query(IncomeForm.category, F.data.startswith("cat:"))
async def income_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(IncomeForm.comment)
    await callback.message.edit_text("Изоҳ ёзинг (ёки /skip):")
    await callback.answer()


@router.message(IncomeForm.comment)
async def income_comment(message: Message, state: FSMContext):
    comment = None if message.text.strip() == "/skip" else message.text.strip()
    await _save_income(message, state, comment)


async def _save_income(message: Message, state: FSMContext, comment):
    data = await state.get_data()
    amount_minor = data["amount_minor"]
    currency = data["currency"]
    method = data["method"]
    category = data.get("category", "salary")

    usd_rate = float(await tx_service.get_setting("usd_rate", "12700"))
    amount_tiyin, usd_rate_used = await to_uzs_tiyin(amount_minor, currency, usd_rate)

    await tx_service.add_transaction(
        kind="income",
        amount_tiyin=amount_tiyin,
        orig_amount_tiyin=amount_minor,
        orig_currency=currency,
        usd_rate_used=usd_rate_used,
        method=method,
        category=category,
        comment=comment,
        source="button",
    )
    await state.clear()

    label = category_label("income", category)
    method_label = "💵 Нақд" if method == "cash" else "💳 Карта"
    await message.answer(
        f"✅ Даромад қайд этилди: {fmt_sum(amount_tiyin)} — {label} ({method_label})",
        reply_markup=main_menu(),
    )
