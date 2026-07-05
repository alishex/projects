import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.config import ADMIN_TO_DEPT
from app.states import OrderStates
from app.keyboards import StartOrderCb, MealStepCb, confirm_keyboard
import app.database as db

logger = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_TO_DEPT


@router.callback_query(StartOrderCb.filter())
async def start_order(call: CallbackQuery, callback_data: StartOrderCb, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer("Sizda ruxsat yo'q.", show_alert=True)
        return

    await call.answer()
    target_date = callback_data.date
    menu = await db.get_menu_item(
        *await _get_cycle(target_date)
    )

    existing = await db.get_order(target_date, ADMIN_TO_DEPT[call.from_user.id]["key"])
    if existing and existing["is_confirmed"]:
        dept = ADMIN_TO_DEPT[call.from_user.id]
        await call.message.answer(
            f"✅ Siz allaqachon buyurtma berdingiz:\n\n"
            f"🥘 Tushlik: <b>{existing['meal1_count']} ta</b>\n"
            f"🌙 Kechki: <b>{existing['meal2_count']} ta</b>\n\n"
            f"O'zgartirish uchun /edit buyrug'ini yuboring.",
            parse_mode="HTML"
        )
        return

    meal1_name, meal2_name = await _get_meal_names(target_date)
    await state.set_state(OrderStates.waiting_meal1)
    await state.update_data(
        target_date=target_date,
        meal1_name=meal1_name,
        meal2_name=meal2_name,
    )
    await call.message.answer(
        f"🥘 <b>Tushlik:</b> {meal1_name}\n\n"
        f"Nechta porsiya buyurtma berasiz?\n"
        f"<i>(Faqat raqam kiriting, masalan: 10)</i>",
        parse_mode="HTML"
    )


@router.message(OrderStates.waiting_meal1)
async def handle_meal1(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return

    count = _parse_int(message.text)
    if count is None:
        await message.answer("❌ Faqat son kiriting! Masalan: <b>10</b>", parse_mode="HTML")
        return

    data = await state.get_data()
    await state.update_data(meal1_count=count)
    await state.set_state(OrderStates.waiting_meal2)
    await message.answer(
        f"✅ Tushlik: <b>{count} ta</b> qabul qilindi\n\n"
        f"🌙 <b>Kechki ovqat:</b> {data['meal2_name']}\n\n"
        f"Nechta porsiya buyurtma berasiz?\n"
        f"<i>(Faqat raqam kiriting, masalan: 5)</i>",
        parse_mode="HTML"
    )


@router.message(OrderStates.waiting_meal2)
async def handle_meal2(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return

    count = _parse_int(message.text)
    if count is None:
        await message.answer("❌ Faqat son kiriting! Masalan: <b>5</b>", parse_mode="HTML")
        return

    data = await state.get_data()
    await state.update_data(meal2_count=count)
    await state.set_state(OrderStates.confirming)

    await message.answer(
        f"📋 <b>Buyurtmangiz:</b>\n\n"
        f"🥘 Tushlik ({data['meal1_name']}): <b>{data['meal1_count']} ta</b>\n"
        f"🌙 Kechki ({data['meal2_name']}): <b>{count} ta</b>\n\n"
        f"Tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=confirm_keyboard(data["target_date"])
    )


@router.callback_query(MealStepCb.filter(F.action == "confirm"))
async def confirm_order(call: CallbackQuery, callback_data: MealStepCb, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer("Sizda ruxsat yo'q.", show_alert=True)
        return

    data = await state.get_data()
    dept = ADMIN_TO_DEPT[call.from_user.id]

    await db.upsert_order(
        date_str=callback_data.date,
        dept_key=dept["key"],
        admin_id=call.from_user.id,
        meal1_count=data.get("meal1_count", 0),
        meal2_count=data.get("meal2_count", 0),
        confirmed=True
    )
    await state.clear()
    await call.answer()
    await call.message.edit_text(
        f"✅ <b>Buyurtma qabul qilindi!</b>\n\n"
        f"🥘 Tushlik: <b>{data.get('meal1_count', 0)} ta</b>\n"
        f"🌙 Kechki: <b>{data.get('meal2_count', 0)} ta</b>\n\n"
        f"Rahmat, {dept['emoji']} {dept['name']}!",
        parse_mode="HTML"
    )
    logger.info(f"Order confirmed: dept={dept['key']} date={callback_data.date} "
                f"m1={data.get('meal1_count')} m2={data.get('meal2_count')}")


@router.callback_query(MealStepCb.filter(F.action == "edit"))
async def edit_order(call: CallbackQuery, callback_data: MealStepCb, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer("Sizda ruxsat yo'q.", show_alert=True)
        return

    await call.answer()
    data = await state.get_data()
    meal1_name, meal2_name = await _get_meal_names(callback_data.date)

    await state.set_state(OrderStates.waiting_meal1)
    await state.update_data(
        target_date=callback_data.date,
        meal1_name=meal1_name,
        meal2_name=meal2_name,
        meal1_count=None,
        meal2_count=None,
    )
    await call.message.answer(
        f"✏️ Qaytadan kiriting:\n\n"
        f"🥘 <b>Tushlik:</b> {meal1_name}\n\n"
        f"Nechta porsiya buyurtma berasiz?\n"
        f"<i>(Faqat raqam kiriting)</i>",
        parse_mode="HTML"
    )


# ── Helpers ────────────────────────────────────────────────────────────────

def _parse_int(text: str | None) -> int | None:
    if not text:
        return None
    text = text.strip()
    if not text.isdigit():
        return None
    val = int(text)
    return val if val >= 0 else None


async def _get_meal_names(target_date: str) -> tuple[str, str]:
    from datetime import date as date_cls
    from app.services.menu_service import get_menu_for_date
    d = date_cls.fromisoformat(target_date)
    menu = await get_menu_for_date(d)
    if menu:
        return menu["meal_1"], menu["meal_2"]
    return "—", "—"


async def _get_cycle(target_date: str):
    from datetime import date as date_cls
    from app.services.menu_service import CYCLE_LABELS, get_menu_for_date
    from app.config import ANCHOR_DATE, ANCHOR_INDEX
    import app.database as _db
    settings = await _db.get_settings()
    anchor_date = settings.get("anchor_date", ANCHOR_DATE)
    anchor_index = int(settings.get("anchor_index", ANCHOR_INDEX))
    anchor = date_cls.fromisoformat(anchor_date)
    d = date_cls.fromisoformat(target_date)
    idx = (anchor_index + (d - anchor).days) % 14
    return CYCLE_LABELS[idx]
