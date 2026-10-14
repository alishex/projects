import csv
import io

from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile

from app.config import OWNER_ID
from app.services import tx_service
from app.categories import category_label

router = Router()
router.message.filter(F.from_user.id == OWNER_ID)

_KIND_LABEL = {"expense": "Харажат", "income": "Даромад"}
_METHOD_LABEL = {"cash": "Нақд", "card": "Карта"}


@router.message(F.text == "📑 Ҳисобот")
async def send_report(message: Message):
    rows = await tx_service.get_all_for_export()
    if not rows:
        await message.answer("Экспорт қиладиган маълумот йўқ.")
        return

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["ID", "Тури", "Summa (som)", "Asl summa", "Asl valyuta", "Usul", "Kategoriya", "Izoh", "Manba", "Sana"]
    )
    for row_id, kind, amount_tiyin, orig_amount, orig_currency, method, category, comment, source, created_at in rows:
        writer.writerow([
            row_id,
            _KIND_LABEL.get(kind, kind),
            amount_tiyin / 100,
            orig_amount / 100,
            orig_currency,
            _METHOD_LABEL.get(method, method),
            category_label(kind, category),
            comment or "",
            source,
            created_at,
        ])

    # utf-8-sig — Excel'da kirill harflari to'g'ri ochilishi uchun (BOM)
    data = buf.getvalue().encode("utf-8-sig")
    file = BufferedInputFile(data, filename="moliya_hisobot.csv")
    await message.answer_document(file, caption="📑 Тўлиқ ҳисобот (CSV)")
