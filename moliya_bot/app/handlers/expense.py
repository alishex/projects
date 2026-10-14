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


class ExpenseForm(StatesGroup):
    amount = State()
    method = State()
    category = State()
    comment = State()


@router.message(F.text == "➕ Харажат")
async def start_expense(message: Message, state: FSMContext):
    await state.set_state(ExpenseForm.amount)
    await message.answer("Миқдорни киритинг (мас: 50000, 1.5 mln, 50 ming, $100):")


@router.message(ExpenseForm.amount)
async def expense_amount(message: Message, state: FSMContext):
    parsed = parse_amount(message.text)
    if parsed is None:
        await message.answer("Тушунмадим, қайта киритинг (мас: 50000 ёки 1.5 mln):")
        return
    amount_minor, currency = parsed
    await state.update_data(amount_minor=amount_minor, currency=currency)
    await state.set_state(ExpenseForm.method)
    await message.answer("Тўлов усули:", reply_markup=method_kb())


@router.callback_query(ExpenseForm.method, F.data.startswith("method:"))
async def expense_method(callback: CallbackQuery, state: FSMContext):
    method = callback.data.split(":")[1]
    await state.update_data(method=method)
    await state.set_state(ExpenseForm.category)
    await callback.message.edit_text("Категория танланг:", reply_markup=category_kb("expense"))
    await callback.answer()


@router.callback_query(ExpenseForm.category, F.data.startswith("cat:"))
async def expense_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(ExpenseForm.comment)
    await callback.message.edit_text("Изоҳ ёзинг (ёки /skip):")
    await callback.answer()


@router.message(ExpenseForm.comment)
async def expense_comment(message: Message, state: FSMContext):
    comment = None if message.text.strip() == "/skip" else message.text.strip()
    await _save_expense(message, state, comment)


async def _save_expense(message: Message, state: FSMContext, comment):
    data = await state.get_data()
    amount_minor = data["amount_minor"]
    currency = data["currency"]
    method = data["method"]
    category = data["category"]

    usd_rate = float(await tx_service.get_setting("usd_rate", "12700"))
    amount_tiyin, usd_rate_used = await to_uzs_tiyin(amount_minor, currency, usd_rate)

    await tx_service.add_transaction(
        kind="expense",
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

    label = category_label("expense", category)
    method_label = "💵 Нақд" if method == "cash" else "💳 Карта"
    await message.answer(
        f"✅ Харажат қайд этилди: {fmt_sum(amount_tiyin)} — {label} ({method_label})",
        reply_markup=main_menu(),
    )

    await _check_alerts(message, category, amount_tiyin)


async def _check_alerts(message: Message, category: str, amount_tiyin: int):
    summary, _, _ = await tx_service.get_summary("month")
    income_total = summary["income"]["total"]
    expense_total = summary["expense"]["total"]

    if expense_total > income_total:
        overage = expense_total - income_total
        await message.answer(
            f"⚠️ Диққат! Бу ой харажатингиз даромадингиздан {fmt_sum(overage)} га ошиб кетди!"
        )

    monthly_limit = int(await tx_service.get_setting("monthly_limit_tiyin", "0"))
    if monthly_limit and expense_total > monthly_limit:
        await message.answer(f"🔴 Ойлик умумий лимитдан ошдингиз! (Лимит: {fmt_sum(monthly_limit)})")

    cat_limit = await tx_service.get_category_limit(category)
    if cat_limit:
        breakdown = await tx_service.get_category_breakdown("month", "expense")
        label = category_label("expense", category)
        cat_spent = next((total for cat_label, total in breakdown if cat_label == label), 0)
        ratio = cat_spent / cat_limit
        if ratio >= 0.8:
            bar = "🔴"
        elif ratio >= 0.6:
            bar = "🟡"
        else:
            bar = None
        if bar:
            await message.answer(
                f"{bar} {label} категорияси лимитнинг {ratio * 100:.0f}% ига етди "
                f"({fmt_sum(cat_spent)} / {fmt_sum(cat_limit)})"
            )
