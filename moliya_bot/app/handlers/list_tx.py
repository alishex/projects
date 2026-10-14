from aiogram import Router, F
from aiogram.types import Message

from app.config import OWNER_ID
from app.services import tx_service
from app.categories import category_label
from app.utils import fmt_sum, fmt_usd

router = Router()
router.message.filter(F.from_user.id == OWNER_ID)


@router.message(F.text == "📋 Рўйхат")
async def show_list(message: Message):
    rows = await tx_service.get_recent(10)
    if not rows:
        await message.answer("Ҳали транзакциялар йўқ.")
        return

    lines = ["📋 <b>Охирги 10 та транзакция:</b>\n"]
    for kind, amount_tiyin, orig_amount, orig_currency, method, category, comment, created_at in rows:
        icon = "📤" if kind == "expense" else "📥"
        method_icon = "💵" if method == "cash" else "💳"
        label = category_label(kind, category)
        date_str = created_at[:16].replace("T", " ")
        amount_str = fmt_sum(amount_tiyin)
        if orig_currency == "USD":
            amount_str += f" ({fmt_usd(orig_amount)})"
        line = f"{icon} {date_str} — {amount_str} {method_icon} — {label}"
        if comment:
            line += f" — <i>{comment}</i>"
        lines.append(line)

    await message.answer("\n".join(lines))
