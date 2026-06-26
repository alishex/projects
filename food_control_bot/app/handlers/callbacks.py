import logging
from datetime import timedelta
from app.utils import today as _today
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import app.database as db
from app.keyboards import (
    MealSelectCB, MealChoiceCB, MealBackCB, MealConfirmCB, ReportMealCB,
    meal_selection_keyboard, meal_choice_keyboard, meal_confirm_keyboard,
    report_meal_keyboard, main_reply_keyboard,
)
from app.services.menu_service import get_tomorrow_menu, format_menu_text
from app.services.order_service import confirm_tomorrow_order, all_confirmed_tomorrow
from app.services.report_service import build_order_report

log = logging.getLogger(__name__)
router = Router()


class UserState(StatesGroup):
    selecting_meal = State()
    waiting_video  = State()


# ── Ovqat tanlash (17:30 inline keyboard) ────────────────────────────────

@router.callback_query(MealSelectCB.filter())
async def cb_meal_select(query: CallbackQuery, callback_data: MealSelectCB,
                          state: FSMContext):
    data = await state.get_data()
    m1 = data.get("m1")
    m2 = data.get("m2")
    meal_num = callback_data.meal

    menu = await get_tomorrow_menu()
    if not menu:
        await query.answer("Menyu topilmadi.", show_alert=True)
        return

    meal_name = menu["meal_1"] if meal_num == 1 else menu["meal_2"]

    await query.message.edit_text(
        f"{meal_num}-ovqat: {meal_name}\n\nBu ovqatni yeysizmi?",
        reply_markup=meal_choice_keyboard(meal_num),
    )
    await query.answer()


@router.callback_query(MealChoiceCB.filter())
async def cb_meal_choice(query: CallbackQuery, callback_data: MealChoiceCB,
                          state: FSMContext, bot: Bot):
    data = await state.get_data()
    m1 = data.get("m1")
    m2 = data.get("m2")

    if callback_data.meal == 1:
        m1 = callback_data.ch
    else:
        m2 = callback_data.ch

    await state.update_data(m1=m1, m2=m2)

    menu = await get_tomorrow_menu()
    if not menu:
        await query.answer()
        return

    # Ikkala ovqat tanlangan bo'lsa — tasdiq oynasiga o'tish
    if m1 is not None and m2 is not None:
        m1_label = "✅ Yeysiz" if m1 == "yes" else "❌ Yemaysiz"
        m2_label = "✅ Yeysiz" if m2 == "yes" else "❌ Yemaysiz"
        text = (
            f"Sizning tanlovingiz:\n\n"
            f"1-ovqat: {menu['meal_1']} — {m1_label}\n"
            f"2-ovqat: {menu['meal_2']} — {m2_label}\n\n"
            "To'g'rimi?"
        )
        await query.message.edit_text(text, reply_markup=meal_confirm_keyboard())
    else:
        # Asosiy tanlash oynasiga qaytish
        text = format_menu_text(menu, m1, m2)
        await query.message.edit_text(text, reply_markup=meal_selection_keyboard(m1, m2))

    await query.answer()


@router.callback_query(MealBackCB.filter())
async def cb_meal_back(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    m1 = data.get("m1")
    m2 = data.get("m2")

    menu = await get_tomorrow_menu()
    if not menu:
        await query.answer()
        return

    text = format_menu_text(menu, m1, m2)
    await query.message.edit_text(text, reply_markup=meal_selection_keyboard(m1, m2))
    await query.answer()


@router.callback_query(MealConfirmCB.filter())
async def cb_meal_confirm(query: CallbackQuery, callback_data: MealConfirmCB,
                           state: FSMContext, bot: Bot):
    if callback_data.act == "edit":
        data = await state.get_data()
        m1 = data.get("m1")
        m2 = data.get("m2")
        menu = await get_tomorrow_menu()
        if menu:
            text = format_menu_text(menu, m1, m2)
            await query.message.edit_text(text, reply_markup=meal_selection_keyboard(m1, m2))
        await query.answer()
        return

    # Tasdiqlash
    data = await state.get_data()
    m1 = data.get("m1")
    m2 = data.get("m2")

    if m1 is None or m2 is None:
        await query.answer("Avval ikkala ovqatni ham tanlang.", show_alert=True)
        return

    tid = query.from_user.id
    await confirm_tomorrow_order(tid, m1, m2)
    await state.clear()
    await query.message.edit_text("✅ Tanlovingiz saqlandi.")
    await query.answer("Saqlandi!")

    # Hamma javob berganda adminga hisobot
    if await all_confirmed_tomorrow():
        settings = await db.get_settings()
        if settings and settings.get("admin_id"):
            tomorrow = (_today() + timedelta(days=1)).isoformat()
            report = await build_order_report(tomorrow)
            try:
                await bot.send_message(
                    settings["admin_id"],
                    f"✅ Barcha xodimlar javob berdi!\n\n{report}"
                )
            except Exception as e:
                log.warning("Admin ga hisobot yubora olmadim: %s", e)


# ── Ovqat hisoboti (qaysi ovqat) ─────────────────────────────────────────

@router.callback_query(ReportMealCB.filter())
async def cb_report_meal(query: CallbackQuery, callback_data: ReportMealCB,
                          state: FSMContext):
    tid = query.from_user.id
    meal_num = callback_data.meal
    today = _today().isoformat()

    order = await db.get_order(today, tid)
    if not order or not order["is_confirmed"]:
        await query.answer(
            "Bugun uchun tasdiqlangan buyurtmangiz yo'q. Ovqat hisoboti faqat ovqat kelgan kuni (ertaga) ishlaydi.",
            show_alert=True
        )
        return

    status = order[f"meal_{meal_num}_status"]
    if status != "yes":
        await query.answer(
            f"Siz {meal_num}-ovqatni \"yemayman\" deb belgilagansiz.", show_alert=True
        )
        return

    # Tekshir — allaqachon video yuborgan
    report = await db.get_user_meal_report(today, tid, meal_num)
    if report:
        await query.answer("Siz allaqachon bu ovqat bo'yicha video yuborgan edingiz.", show_alert=True)
        return

    await state.update_data(report_meal=meal_num, report_date=today)
    await state.set_state(UserState.waiting_video)

    from app.services.menu_service import get_today_menu
    menu = await get_today_menu()
    meal_name = ""
    if menu:
        meal_name = f" — {menu['meal_1'] if meal_num == 1 else menu['meal_2']}"

    await query.message.edit_text(
        f"Yeb bo'lgan ovqatingiz idishini hisobot tarzida round video qilib tashlab bering.\n\n"
        f"Ovqat: {meal_num}-ovqat{meal_name}"
    )
    await query.answer()
