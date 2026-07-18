import asyncio
import logging
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.config import DEPT_BY_KEY, ADMIN_DEPTS, ADMIN_IDS
from app.states import OrderStates
from app.keyboards import StartOrderCb, MealStepCb, EditPickCb, confirm_keyboard, edit_pick_keyboard
import app.database as db

logger = logging.getLogger(__name__)
router = Router()

# Har bir admin uchun alohida lock — bitta chatdan bir vaqtda kelgan ikki
# callback (double-tap yoki tarmoq qayta urinishi) confirm_order'ni bir vaqtda
# ishga tushirib, FSM state'ni ikki marta o'qib qolishining oldini oladi.
_confirm_locks: dict[int, asyncio.Lock] = {}


def _get_confirm_lock(user_id: int) -> asyncio.Lock:
    lock = _confirm_locks.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _confirm_locks[user_id] = lock
    return lock


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.callback_query(StartOrderCb.filter())
async def start_order(call: CallbackQuery, callback_data: StartOrderCb, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer("Sizda ruxsat yo'q.", show_alert=True)
        return

    # Bo'lim endi tugma bilan birga keladi (callback_data.dept_key), global
    # bitta-adminga-bitta-bo'lim lug'atidan emas — shunda bitta admin bir
    # nechta bo'limga mas'ul bo'lsa, har bir tugma o'z bo'limini to'g'ri
    # aniqlaydi. Baribir shu admin haqiqatan ham shu bo'limga tayinlanganini
    # tekshiramiz (masalan .env keyin o'zgargan bo'lsa, eski tugma ishlamasin).
    dept = DEPT_BY_KEY.get(callback_data.dept_key)
    if dept is None or dept.get("admin_id") != call.from_user.id:
        await call.answer("Sizda ruxsat yo'q.", show_alert=True)
        return

    await call.answer()
    target_date = callback_data.date
    menu = await db.get_menu_item(
        *await _get_cycle(target_date)
    )

    existing = await db.get_order(target_date, dept["key"])
    if existing and existing["is_confirmed"]:
        await call.message.answer(
            f"✅ Siz allaqachon buyurtma berdingiz ({dept['emoji']} {dept['name']}):\n\n"
            f"🥘 Tushlik: <b>{existing['meal1_count']} ta</b>\n"
            f"🌙 Kechki: <b>{existing['meal2_count']} ta</b>\n\n"
            f"O'zgartirish uchun /edit buyrug'ini yuboring.",
            parse_mode="HTML"
        )
        return

    current_state = await state.get_state()
    if current_state is not None:
        data = await state.get_data()
        if data.get("target_date") == target_date and data.get("dept_key") == dept["key"]:
            # Xuddi shu bo'lim/kun uchun tugma qayta bosilgan — tozalab
            # qaytadan boshlaymiz.
            await state.clear()
        else:
            # Boshqa bo'lim (yoki boshqa kun)ga tegishli oqim hali
            # tugallanmagan — ustidan yozib yubormaymiz, aks holda admin
            # bitta bo'lim uchun kiritgan sonlari sezdirmasdan yo'qolib
            # qolishi mumkin (endi bitta admin bir nechta bo'limga mas'ul
            # bo'lishi mumkin, shuning uchun bu holat kundalik uchrashi mumkin).
            prev_dept = DEPT_BY_KEY.get(data.get("dept_key"))
            prev_label = f"{prev_dept['emoji']} {prev_dept['name']}" if prev_dept else "boshqa buyurtma"
            await call.message.answer(
                f"⚠️ Sizda tugallanmagan buyurtma bor ({prev_label}).\n"
                f"Avval uni yakunlang yoki /cancel yozing."
            )
            return

    meal1_name, meal2_name = await _get_meal_names(target_date)
    await state.set_state(OrderStates.waiting_meal1)
    await state.update_data(
        target_date=target_date,
        dept_key=dept["key"],
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

    async with _get_confirm_lock(call.from_user.id):
        current_state = await state.get_state()
        data = await state.get_data()
        dept = DEPT_BY_KEY.get(data.get("dept_key"))

        # Eskirgan (avvalgi kunga yoki, endi bitta admin bir nechta bo'limga
        # mas'ul bo'lishi mumkinligi sababli, boshqa bo'limga tegishli) tugma
        # yoki takroriy bosish — bunday holatlarda state allaqachon
        # tozalangan yoki boshqa sana/bo'limga tegishli bo'ladi, shu yerda
        # ushlab qolamiz.
        if current_state != OrderStates.confirming or data.get("target_date") != callback_data.date or dept is None:
            await call.answer("Bu tugma eskirgan. Iltimos, /edit buyrug'i bilan qaytadan kiriting.", show_alert=True)
            return

        meal1_count = data["meal1_count"]
        meal2_count = data["meal2_count"]

        # State'ni yozishdan OLDIN tozalaymiz — shu bilan ikkinchi (parallel
        # yoki keyingi) chaqiruv yuqoridagi tekshiruvdan o'tolmaydi.
        await state.clear()

        try:
            await db.upsert_order(
                date_str=callback_data.date,
                dept_key=dept["key"],
                admin_id=call.from_user.id,
                meal1_count=meal1_count,
                meal2_count=meal2_count,
                confirmed=True
            )
        except Exception as e:
            logger.error(f"confirm_order: DB yozishda xato — dept={dept['key']} date={callback_data.date}: {e}")
            await call.answer("❌ Xatolik yuz berdi, qayta urinib ko'ring.", show_alert=True)
            return

        await call.answer()
        await call.message.edit_text(
            f"✅ <b>Buyurtma qabul qilindi!</b>\n\n"
            f"🥘 Tushlik: <b>{meal1_count} ta</b>\n"
            f"🌙 Kechki: <b>{meal2_count} ta</b>\n\n"
            f"Rahmat, {dept['emoji']} {dept['name']}!",
            parse_mode="HTML"
        )
        logger.info(f"Order confirmed: dept={dept['key']} date={callback_data.date} "
                    f"m1={meal1_count} m2={meal2_count}")


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
        f"✏️ Qaytadan kiriting ({callback_data.date}):\n\n"
        f"🥘 <b>Tushlik:</b> {meal1_name}\n\n"
        f"Nechta porsiya buyurtma berasiz?\n"
        f"<i>(Faqat raqam kiriting)</i>",
        parse_mode="HTML"
    )


@router.message(Command("edit"))
async def cmd_edit(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return

    depts = ADMIN_DEPTS.get(message.from_user.id, [])
    if len(depts) > 1:
        # Bitta admin bir nechta bo'limga mas'ul — qaysi birini tahrirlashni
        # so'raymiz, chunki buyruq matnidan buni bilib bo'lmaydi.
        await message.answer(
            "Qaysi bo'lim uchun tahrirlaysiz?",
            reply_markup=edit_pick_keyboard(depts)
        )
        return

    await _begin_edit(message, state, depts[0])


@router.callback_query(EditPickCb.filter())
async def edit_pick(call: CallbackQuery, callback_data: EditPickCb, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer("Sizda ruxsat yo'q.", show_alert=True)
        return

    dept = DEPT_BY_KEY.get(callback_data.dept_key)
    if dept is None or dept.get("admin_id") != call.from_user.id:
        await call.answer("Sizda ruxsat yo'q.", show_alert=True)
        return

    await call.answer()
    await _begin_edit(call.message, state, dept)


async def _begin_edit(target: Message, state: FSMContext, dept: dict):
    from datetime import date as date_cls, timedelta
    target_date = (date_cls.today() + timedelta(days=1)).isoformat()

    existing = await db.get_order(target_date, dept["key"])
    if not existing:
        await target.answer(
            f"Tahrirlash uchun avval tasdiqlangan buyurtma topilmadi ({dept['emoji']} {dept['name']})."
        )
        return

    meal1_name, meal2_name = await _get_meal_names(target_date)
    await state.set_state(OrderStates.waiting_meal1)
    await state.update_data(
        target_date=target_date,
        dept_key=dept["key"],
        meal1_name=meal1_name,
        meal2_name=meal2_name,
    )
    await target.answer(
        f"✏️ Qaytadan kiriting ({dept['emoji']} {dept['name']}):\n\n"
        f"🥘 <b>Tushlik:</b> {meal1_name}\n\n"
        f"Nechta porsiya buyurtma berasiz?\n"
        f"<i>(Faqat raqam kiriting)</i>",
        parse_mode="HTML"
    )


@router.message(Command("cancel"), StateFilter(OrderStates))
async def cmd_cancel(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("❌ Bekor qilindi.")


# ── Helpers ────────────────────────────────────────────────────────────────

def _parse_int(text: str | None) -> int | None:
    if not text:
        return None
    text = text.strip()
    try:
        val = int(text)
    except ValueError:
        return None
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
