import os
import tempfile

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import OWNER_ID
from app.services import tx_service, nlu_service, voice_service
from app.services.fx_service import to_uzs_tiyin
from app.categories import category_label
from app.utils import fmt_sum

router = Router()
router.message.filter(F.from_user.id == OWNER_ID)
router.callback_query.filter(F.from_user.id == OWNER_ID)

# Bitta egasi bo'lgan bot uchun jarayon-ichi vaqtinchalik xotira yetarli —
# FSM holatini band qilmaslik uchun ataylab alohida saqlanadi.
_pending = {}


@router.message(F.voice)
async def handle_voice(message: Message, state: FSMContext):
    if await state.get_state() is not None:
        await message.answer("Аввал жорий амални якунланг ёки /cancel ёзинг.")
        return

    voice_enabled = await tx_service.get_setting("voice_enabled", "1")
    if voice_enabled != "1":
        await message.answer("Овозли киритиш ўчирилган (⚙️ Созлашдан ёқишингиз мумкин).")
        return

    status = await message.answer("🎙 Овоз эшитилмоқда...")
    tmp_path = None
    try:
        file = await message.bot.get_file(message.voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as tmp:
            tmp_path = tmp.name
        await message.bot.download_file(file.file_path, tmp_path)
        text = await voice_service.transcribe(tmp_path)
    except Exception:
        await status.edit_text("❌ Овозни матнга ўгиришда хато юз берди. Ёзма киритиб кўринг.")
        return
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    if not text.strip():
        await status.edit_text("Овозни тушунмадим, қайта уриниб кўринг.")
        return

    await status.edit_text(f"🎙 Эшитилди: <i>«{text}»</i>")
    await _process_freeform(message, text)


@router.message(F.text, ~F.text.startswith("/"))
async def handle_text(message: Message, state: FSMContext):
    if await state.get_state() is not None:
        return
    await _process_freeform(message, message.text)


async def _process_freeform(message: Message, text: str):
    result = await nlu_service.parse_free_text(text)

    if result is None:
        await message.answer(
            "Эркин матн таҳлили ҳозир созланмаган. Тугмалардан фойдаланинг (➕ Харажат / 📥 Даромад)."
        )
        return
    if result == "error":
        await message.answer(
            "Таҳлил хизмати ҳозир жавоб бермаяпти (эҳтимол баланс тугаган). Тугмалардан фойдаланинг."
        )
        return
    if result.get("needs_clarification"):
        await message.answer(
            "Тўлиқ тушунмадим — тугмалар орқали аниқроқ киритинг (➕ Харажат / 📥 Даромад), "
            "ёки батафсилроқ ёзиб кўринг (мас: «50 минг таксига нақд кетди»)."
        )
        return

    kind = result["kind"]
    amount = result["amount"]
    currency = result["currency"]
    method = result["method"]
    category = result["category"]
    comment = result.get("comment") or text

    amount_minor = round(amount * 100)
    usd_rate = float(await tx_service.get_setting("usd_rate", "12700"))
    amount_tiyin, usd_rate_used = await to_uzs_tiyin(amount_minor, currency, usd_rate)

    key = str(message.from_user.id)
    _pending[key] = {
        "kind": kind,
        "amount_tiyin": amount_tiyin,
        "orig_amount_tiyin": amount_minor,
        "orig_currency": currency,
        "usd_rate_used": usd_rate_used,
        "method": method,
        "category": category,
        "comment": comment,
    }

    label = category_label(kind, category)
    method_label = "💵 Нақд" if method == "cash" else "💳 Карта"
    kind_label = "Харажат" if kind == "expense" else "Даромад"

    b = InlineKeyboardBuilder()
    b.button(text="✅ Сақлаш", callback_data="ff:confirm")
    b.button(text="❌ Бекор қилиш", callback_data="ff:cancel")
    b.adjust(2)

    await message.answer(
        f"Тушундим: <b>{kind_label}</b>\n{fmt_sum(amount_tiyin)} — {label} ({method_label})\n"
        f"«{comment}»\n\nСақлайми?",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data == "ff:confirm")
async def ff_confirm(callback: CallbackQuery):
    key = str(callback.from_user.id)
    data = _pending.pop(key, None)
    if not data:
        await callback.answer("Муддати ўтган, қайта уриниб кўринг.")
        return
    await tx_service.add_transaction(
        kind=data["kind"],
        amount_tiyin=data["amount_tiyin"],
        orig_amount_tiyin=data["orig_amount_tiyin"],
        orig_currency=data["orig_currency"],
        usd_rate_used=data["usd_rate_used"],
        method=data["method"],
        category=data["category"],
        comment=data["comment"],
        source="text",
    )
    await callback.message.edit_text("✅ Сақланди.")
    await callback.answer()


@router.callback_query(F.data == "ff:cancel")
async def ff_cancel(callback: CallbackQuery):
    _pending.pop(str(callback.from_user.id), None)
    await callback.message.edit_text("❌ Бекор қилинди.")
    await callback.answer()
