from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from app.config import OWNER_ID
from app.keyboards import period_kb
from app.services import tx_service
from app.utils import fmt_sum, PERIOD_LABELS

router = Router()
router.message.filter(F.from_user.id == OWNER_ID)
router.callback_query.filter(F.from_user.id == OWNER_ID)


@router.message(F.text == "📊 Дашборд")
async def dashboard_menu(message: Message):
    await message.answer("Даврни танланг:", reply_markup=period_kb())


@router.callback_query(F.data.startswith("period:"))
async def dashboard_show(callback: CallbackQuery):
    period = callback.data.split(":")[1]
    text = await _render_dashboard(period)
    await callback.message.edit_text(text, reply_markup=period_kb())
    await callback.answer()


async def _render_dashboard(period: str) -> str:
    summary, start, end = await tx_service.get_summary(period)
    income = summary["income"]
    expense = summary["expense"]

    lines = [f"📊 <b>{PERIOD_LABELS[period]} дашборд</b> ({start.strftime('%d.%m')}–{end.strftime('%d.%m')})\n"]

    lines.append("📥 <b>Даромад</b>")
    lines.append(f"  💵 Нақд: {fmt_sum(income['cash'])}")
    lines.append(f"  💳 Карта: {fmt_sum(income['card'])}")
    lines.append(f"  <b>ЯКУНИЙ: {fmt_sum(income['total'])}</b>\n")

    lines.append("📤 <b>Харажат</b>")
    lines.append(f"  💵 Нақд: {fmt_sum(expense['cash'])}")
    lines.append(f"  💳 Карта: {fmt_sum(expense['card'])}")
    lines.append(f"  <b>ЯКУНИЙ: {fmt_sum(expense['total'])}</b>\n")

    balance = summary["balance"]
    verdict = "✅ Етарли" if balance >= 0 else "⚠️ Етарли эмас"
    state_word = "ортиқча" if balance >= 0 else "камомад"
    lines.append(f"💰 <b>Баланс: {fmt_sum(abs(balance))}</b> ({state_word}) — {verdict}")

    if income["total"] > 0:
        pct = (expense["total"] / income["total"]) * 100
        lines.append(f"📈 Харажат даромаднинг {pct:.0f}% ини ташкил этади")

    breakdown = await tx_service.get_category_breakdown(period, "expense")
    if breakdown:
        lines.append("\n📦 <b>Харажат категориялар бўйича:</b>")
        for label, total in breakdown[:8]:
            lines.append(f"  {label}: {fmt_sum(total)}")

    return "\n".join(lines)
