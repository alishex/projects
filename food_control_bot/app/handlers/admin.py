import logging
from datetime import timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import app.database as db
import app.config as cfg
import app.scheduler as sched
from app.utils import today as _today
from app.services.menu_service import (
    get_today_menu, get_tomorrow_menu, format_menu_text, CYCLE_LABELS
)
from app.services.report_service import build_order_report, build_final_report
from app.keyboards import (
    AdminPanelCB, AdminEditOrderCB, AdminToggleMealCB,
    AdminEmployeeRemoveCB, AdminEmployeeAddCB,
    AdminAdminAddCB, AdminAdminRemoveCB,
    AdminScheduleEditCB, AdminMenuWeekCB, AdminMenuDayCB, AdminMenuEditStartCB,
    AdminCycleSetCB,
    admin_main_keyboard, admin_back_keyboard,
    admin_edit_list_keyboard, admin_edit_user_keyboard,
    admin_employees_keyboard, admin_admins_keyboard, admin_schedule_keyboard,
    admin_menu_week_keyboard, admin_menu_day_keyboard, admin_menu_day_detail_keyboard,
    admin_cycle_keyboard,
)

log = logging.getLogger(__name__)
router = Router()


class AdminSetup(StatesGroup):
    waiting_employees = State()
    waiting_group     = State()
    waiting_menu      = State()


class AdminEdit(StatesGroup):
    waiting_employee_id  = State()
    waiting_admin_id     = State()
    waiting_schedule_time = State()
    waiting_menu_day_text = State()


def is_admin_id(telegram_id: int) -> bool:
    return telegram_id in cfg.ADMIN_IDS


def _extract_id_from_message(msg: Message) -> "int | None":
    """Xodim/admin ID sini oladi: forward qilingan xabardan yoki qo'lda kiritilgan raqamdan."""
    if msg.forward_from:
        return msg.forward_from.id
    text = (msg.text or "").strip()
    if text.lstrip("-").isdigit():
        return int(text)
    return None


def _dn(u: dict) -> str:
    if u.get("username"):
        return f"@{u['username']}"
    return u.get("full_name") or f"User_{u['telegram_id']}"


# ── /start ────────────────────────────────────────────────────────────────

@router.message(Command("start"), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def admin_start(msg: Message, state: FSMContext):
    await db.add_or_update_user(
        telegram_id=msg.from_user.id,
        full_name=msg.from_user.full_name,
        username=msg.from_user.username,
        role="admin",
        has_started=1,
    )

    settings = await db.get_settings()
    if not settings:
        await msg.answer(
            "Marketing bo'limining ovqat nazorati botiga xush kelibsiz.\n\n"
            "Xodimlarning Telegram ID raqamlarini yuboring.\n"
            "Har bir ID ni yangi qatordan yozing.\n"
            "Jami 12 ta xodim ID yuborilishi kerak."
        )
        await state.set_state(AdminSetup.waiting_employees)
    else:
        await msg.answer(
            "Marketing bo'limining ovqat nazorati botiga xush kelibsiz.\n\n"
            "/admin — Admin panel\n\n"
            "Buyruqlar:\n"
            "/set_users — xodimlar ID ro'yxatini yangilash\n"
            "/set_group — hisobot guruh ID sini o'zgartirish\n"
            "/set_menu  — menyu tahrirlash\n"
            "/set_cycle — siklni sozlash\n"
            "/report    — ertangi buyurtmalar hisoboti\n"
            "/today     — bugungi menyu\n"
            "/tomorrow  — ertangi menyu\n"
            "/reset_day — bugungi buyurtmalarni tozalash"
        )


@router.message(AdminSetup.waiting_employees)
async def receive_employees(msg: Message, state: FSMContext):
    lines = [l.strip() for l in msg.text.strip().splitlines() if l.strip()]
    ids = []
    errors = []
    for line in lines:
        try:
            ids.append(int(line))
        except ValueError:
            errors.append(line)

    if errors:
        await msg.answer(
            f"❌ Quyidagi qatorlar noto'g'ri (faqat raqam bo'lishi kerak):\n"
            + "\n".join(errors)
            + "\n\nQaytadan 12 ta ID yuboring."
        )
        return

    if len(ids) != 12:
        await msg.answer(
            f"❌ {len(ids)} ta ID yuborildi. Aynan 12 ta kerak.\nQaytadan yuboring."
        )
        return

    await db.clear_employees()
    for tid in ids:
        await db.add_employee_id(tid)

    await db.add_or_update_user(
        telegram_id=msg.from_user.id,
        full_name=msg.from_user.full_name,
        username=msg.from_user.username,
        role="admin",
        has_started=1,
    )

    await state.update_data(employee_ids=ids)
    await msg.answer(
        f"✅ {len(ids)} ta xodim + admin qo'shildi. Jami: {len(ids)+1} kishi.\n\n"
        "Endi hisobot yuboriladigan Telegram guruh ID sini yuboring."
    )
    await state.set_state(AdminSetup.waiting_group)


@router.message(AdminSetup.waiting_group)
async def receive_group(msg: Message, state: FSMContext):
    try:
        group_id = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Guruh ID faqat raqam bo'lishi kerak. Qaytadan yuboring.")
        return

    await db.save_settings(
        admin_id=msg.from_user.id,
        group_id=group_id,
        anchor_date=cfg.ANCHOR_DATE,
        anchor_week=cfg.ANCHOR_WEEK,
        anchor_day=cfg.ANCHOR_DAY,
        anchor_index=cfg.ANCHOR_INDEX,
    )
    await state.clear()
    await msg.answer(
        "✅ Sozlamalar saqlandi!\n\n"
        f"Guruh ID: <code>{group_id}</code>\n\n"
        "Bot tayyor. Har kuni 13:30 da ertangi taomnoma yuboriladi.\n"
        "22:00 da yakuniy hisobot guruhga va sizga yuboriladi.\n\n"
        "/admin — Admin panel"
    )


# ── /admin ────────────────────────────────────────────────────────────────

@router.message(Command("admin"), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cmd_admin_panel(msg: Message):
    await msg.answer(
        "🔧 <b>Admin Panel</b>\n\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=admin_main_keyboard(),
    )


@router.callback_query(AdminPanelCB.filter(), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cb_admin_panel(query: CallbackQuery, callback_data: AdminPanelCB):
    section = callback_data.section

    if section == "main":
        await query.message.edit_text(
            "🔧 <b>Admin Panel</b>\n\nQuyidagi bo'limlardan birini tanlang:",
            reply_markup=admin_main_keyboard(),
        )

    elif section == "status":
        text = await _build_status_text()
        await query.message.edit_text(
            text, reply_markup=admin_back_keyboard(refresh_section="status")
        )

    elif section == "employees":
        text = await _build_employees_text()
        users = await db.get_all_active_users()
        employees = [u for u in users if u.get("role") != "admin"]
        await query.message.edit_text(
            text, reply_markup=admin_employees_keyboard(employees)
        )

    elif section == "tomorrow":
        tomorrow = (_today() + timedelta(days=1)).isoformat()
        text = await build_order_report(tomorrow)
        await query.message.edit_text(
            text, reply_markup=admin_back_keyboard(refresh_section="tomorrow")
        )

    elif section == "settings":
        settings = await db.get_settings()
        group_id = settings.get("group_id") if settings else "—"
        text = (
            "⚙️ <b>Sozlamalar</b>\n\n"
            f"Guruh ID: <code>{group_id}</code>\n\n"
            "Xodimlar, adminlar, menyu, sikl va vaqtlarni asosiy panel tugmalari orqali boshqarishingiz mumkin.\n\n"
            "Qo'shimcha matnli buyruqlar:\n"
            "/set_users — xodimlar ID ro'yxatini to'liq almashtirish (12 ta)\n"
            "/set_group — hisobot guruh ID sini o'zgartirish\n"
            "/set_menu  — menyuni bir vaqtda to'liq qayta yozish\n"
            "/reset_day — bugungi buyurtmalarni tozalash"
        )
        await query.message.edit_text(
            text, reply_markup=admin_back_keyboard()
        )

    elif section == "edit":
        text, kb = await _build_edit_list()
        await query.message.edit_text(text, reply_markup=kb)

    elif section == "schedule":
        settings = await db.get_settings()
        menu_time = (settings or {}).get("menu_send_time") or "13:30"
        report_time = (settings or {}).get("report_time") or "22:00"
        text = (
            "🕐 <b>Vaqtlar</b>\n\n"
            f"Menyu yuborish vaqti: <code>{menu_time}</code>\n"
            f"Yakuniy hisobot vaqti: <code>{report_time}</code>\n\n"
            "O'zgartirish uchun tugmani bosing."
        )
        await query.message.edit_text(text, reply_markup=admin_schedule_keyboard())

    elif section == "admins":
        admins = await db.get_admin_users()
        text = (
            f"👑 <b>Adminlar</b> (jami {len(admins)} kishi)\n\n"
            + "\n".join(f"  {'👑' if u['telegram_id'] == cfg.SUPER_ADMIN_ID else '•'} {_dn(u)}" for u in admins)
        )
        await query.message.edit_text(
            text, reply_markup=admin_admins_keyboard(admins, cfg.SUPER_ADMIN_ID)
        )

    elif section == "menu_edit":
        await query.message.edit_text(
            "📝 <b>Menyu tahrirlash</b>\n\nHaftani tanlang:",
            reply_markup=admin_menu_week_keyboard(),
        )

    elif section == "cycle":
        await query.message.edit_text(
            "🔄 <b>Sikl sozlash</b>\n\n"
            "Bugun aslida qaysi hafta/kun menyusi bo'lishi kerakligini tanlang "
            "(sikl bugungi sanaga bog'lab qo'yiladi):",
            reply_markup=admin_cycle_keyboard(),
        )

    await query.answer()


@router.callback_query(AdminEditOrderCB.filter(), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cb_admin_edit_order(query: CallbackQuery, callback_data: AdminEditOrderCB):
    """Bitta xodimning buyurtmasini ko'rsatish va tahrirlash."""
    user_id = callback_data.user_id
    tomorrow = (_today() + timedelta(days=1)).isoformat()

    user = await db.get_user(user_id)
    order = await db.get_order(tomorrow, user_id)

    from app.services.menu_service import get_menu_for_date
    from datetime import date as dt
    menu = await get_menu_for_date(dt.fromisoformat(tomorrow))

    name = _dn(user) if user else f"User_{user_id}"
    m1_name = menu["meal_1"] if menu else "1-ovqat"
    m2_name = menu["meal_2"] if menu else "2-ovqat"

    if order and order.get("is_confirmed"):
        m1_st = order["meal_1_status"]
        m2_st = order["meal_2_status"]
        m1_icon = "✅ Yeydi" if m1_st == "yes" else "❌ Yemaydi"
        m2_icon = "✅ Yeydi" if m2_st == "yes" else "❌ Yemaydi"
    else:
        m1_st = m2_st = None
        m1_icon = m2_icon = "⏳ Javob bermagan"

    text = (
        f"✏️ <b>{name}</b> buyurtmasini tahrirlash\n"
        f"📅 {menu['week_label'] if menu else tomorrow}\n\n"
        f"<b>1-ovqat:</b> {m1_name}\n"
        f"Holat: {m1_icon}\n\n"
        f"<b>2-ovqat:</b> {m2_name}\n"
        f"Holat: {m2_icon}"
    )
    await query.message.edit_text(
        text,
        reply_markup=admin_edit_user_keyboard(user_id, m1_st, m2_st)
    )
    await query.answer()


@router.callback_query(AdminToggleMealCB.filter(), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cb_admin_toggle_meal(query: CallbackQuery, callback_data: AdminToggleMealCB, bot: Bot):
    """Xodimning bitta ovqat holatini toggle qilish va xodimga xabar yuborish."""
    user_id = callback_data.user_id
    meal = callback_data.meal
    tomorrow = (_today() + timedelta(days=1)).isoformat()

    order = await db.get_order(tomorrow, user_id)
    current = None
    if order and order.get("is_confirmed"):
        current = order[f"meal_{meal}_status"]

    new_status = "no" if current == "yes" else "yes"
    await db.admin_toggle_meal(tomorrow, user_id, meal, new_status)

    from app.services.menu_service import get_menu_for_date
    from datetime import date as dt
    menu = await get_menu_for_date(dt.fromisoformat(tomorrow))
    meal_name = (menu["meal_1"] if meal == 1 else menu["meal_2"]) if menu else f"{meal}-ovqat"
    menu_label = menu["week_label"] if menu else tomorrow

    old_icon = "✅ Yeydi" if current == "yes" else ("❌ Yemaydi" if current == "no" else "⏳ belgilanmagan")
    new_icon = "✅ Yeydi" if new_status == "yes" else "❌ Yemaydi"

    await query.answer(f"{meal}-ovqat: {new_icon}", show_alert=False)

    # Xodimga xabar yuborish
    user = await db.get_user(user_id)
    try:
        await bot.send_message(
            user_id,
            f"ℹ️ Admin sizning buyurtmangizni o'zgartirdi.\n\n"
            f"📅 {menu_label}\n"
            f"{meal}-ovqat: {meal_name}\n\n"
            f"{old_icon} → {new_icon}"
        )
    except Exception as e:
        log.warning("Xodim %s ga buyurtma o'zgarishi haqida xabar yubora olmadim: %s", user_id, e)

    # Edit screen yangilash
    order = await db.get_order(tomorrow, user_id)
    name = _dn(user) if user else f"User_{user_id}"
    m1_name = menu["meal_1"] if menu else "1-ovqat"
    m2_name = menu["meal_2"] if menu else "2-ovqat"

    m1_st = order["meal_1_status"] if order else None
    m2_st = order["meal_2_status"] if order else None
    m1_icon = "✅ Yeydi" if m1_st == "yes" else "❌ Yemaydi" if m1_st == "no" else "⏳"
    m2_icon = "✅ Yeydi" if m2_st == "yes" else "❌ Yemaydi" if m2_st == "no" else "⏳"

    text = (
        f"✏️ <b>{name}</b> buyurtmasini tahrirlash\n"
        f"📅 {menu_label}\n\n"
        f"<b>1-ovqat:</b> {m1_name}\n"
        f"Holat: {m1_icon}\n\n"
        f"<b>2-ovqat:</b> {m2_name}\n"
        f"Holat: {m2_icon}"
    )
    await query.message.edit_text(
        text,
        reply_markup=admin_edit_user_keyboard(user_id, m1_st, m2_st)
    )


# ── Xodimlarni birma-bir boshqarish ─────────────────────────────────────────

@router.callback_query(AdminEmployeeRemoveCB.filter(), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cb_admin_employee_remove(query: CallbackQuery, callback_data: AdminEmployeeRemoveCB):
    await db.remove_employee(callback_data.user_id)
    text = await _build_employees_text()
    users = await db.get_all_active_users()
    employees = [u for u in users if u.get("role") != "admin"]
    await query.message.edit_text(text, reply_markup=admin_employees_keyboard(employees))
    await query.answer("✅ Xodim o'chirildi.")


@router.callback_query(AdminEmployeeAddCB.filter(), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cb_admin_employee_add(query: CallbackQuery, state: FSMContext):
    await state.set_state(AdminEdit.waiting_employee_id)
    await query.message.edit_text(
        "➕ <b>Xodim qo'shish</b>\n\n"
        "Xodimning Telegram ID raqamini yuboring,\n"
        "yoki uning istalgan xabarini shu chatga forward qiling.",
        reply_markup=admin_back_keyboard(),
    )
    await query.answer()


@router.message(AdminEdit.waiting_employee_id)
async def receive_new_employee(msg: Message, state: FSMContext):
    tid = _extract_id_from_message(msg)
    if tid is None:
        await msg.answer("❌ ID topilmadi. Raqam yuboring yoki xabarni forward qiling.")
        return
    await db.add_employee_id(tid)
    await state.clear()
    await msg.answer(f"✅ Xodim qo'shildi (ID: <code>{tid}</code>).\n\n/admin — panelga qaytish")


# ── Adminlarni boshqarish ───────────────────────────────────────────────────

@router.callback_query(AdminAdminAddCB.filter(), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cb_admin_admin_add(query: CallbackQuery, state: FSMContext):
    await state.set_state(AdminEdit.waiting_admin_id)
    await query.message.edit_text(
        "➕ <b>Admin qo'shish</b>\n\n"
        "Yangi adminning Telegram ID raqamini yuboring,\n"
        "yoki uning istalgan xabarini shu chatga forward qiling.",
        reply_markup=admin_back_keyboard(),
    )
    await query.answer()


@router.message(AdminEdit.waiting_admin_id)
async def receive_new_admin(msg: Message, state: FSMContext):
    tid = _extract_id_from_message(msg)
    if tid is None:
        await msg.answer("❌ ID topilmadi. Raqam yuboring yoki xabarni forward qiling.")
        return
    await db.set_user_role(tid, "admin")
    await db.refresh_admin_ids()
    await state.clear()
    await msg.answer(f"✅ Yangi admin qo'shildi (ID: <code>{tid}</code>).\n\n/admin — panelga qaytish")


@router.callback_query(AdminAdminRemoveCB.filter(), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cb_admin_admin_remove(query: CallbackQuery, callback_data: AdminAdminRemoveCB):
    if callback_data.user_id == cfg.SUPER_ADMIN_ID:
        await query.answer("❌ Bosh adminni olib tashlab bo'lmaydi.", show_alert=True)
        return
    await db.set_user_role(callback_data.user_id, "employee")
    await db.refresh_admin_ids()
    admins = await db.get_admin_users()
    text = (
        f"👑 <b>Adminlar</b> (jami {len(admins)} kishi)\n\n"
        + "\n".join(f"  {'👑' if u['telegram_id'] == cfg.SUPER_ADMIN_ID else '•'} {_dn(u)}" for u in admins)
    )
    await query.message.edit_text(text, reply_markup=admin_admins_keyboard(admins, cfg.SUPER_ADMIN_ID))
    await query.answer("✅ Admin huquqi olib tashlandi.")


# ── Vaqtlarni sozlash ────────────────────────────────────────────────────────

@router.callback_query(AdminScheduleEditCB.filter(), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cb_admin_schedule_edit(query: CallbackQuery, callback_data: AdminScheduleEditCB, state: FSMContext):
    await state.update_data(schedule_field=callback_data.field)
    await state.set_state(AdminEdit.waiting_schedule_time)
    label = "Menyu yuborish" if callback_data.field == "menu" else "Yakuniy hisobot"
    await query.message.edit_text(
        f"✏️ <b>{label} vaqti</b>\n\n"
        "Yangi vaqtni HH:MM formatida yuboring (masalan: 14:00).",
        reply_markup=admin_back_keyboard(),
    )
    await query.answer()


@router.message(AdminEdit.waiting_schedule_time)
async def receive_schedule_time(msg: Message, state: FSMContext):
    text = (msg.text or "").strip()
    try:
        hh_str, mm_str = text.split(":")
        hh, mm = int(hh_str), int(mm_str)
        assert 0 <= hh <= 23 and 0 <= mm <= 59
    except (ValueError, AssertionError):
        await msg.answer("❌ Format noto'g'ri. HH:MM ko'rinishida yuboring (masalan: 14:00).")
        return

    data = await state.get_data()
    field = data.get("schedule_field")
    await state.clear()

    if field == "menu":
        await sched.reschedule_menu_time(hh, mm)
        await msg.answer(f"✅ Menyu yuborish vaqti <code>{hh:02d}:{mm:02d}</code> ga o'zgartirildi.\n\n/admin")
    elif field == "report":
        await sched.reschedule_report_time(hh, mm)
        await msg.answer(f"✅ Yakuniy hisobot vaqti <code>{hh:02d}:{mm:02d}</code> ga o'zgartirildi.\n\n/admin")
    else:
        await msg.answer("❌ Xatolik: qaysi vaqt ekani aniqlanmadi. /admin dan qaytadan urinib ko'ring.")


# ── Menyu tahrirlash (tugmali) ───────────────────────────────────────────────

@router.callback_query(AdminMenuWeekCB.filter(), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cb_admin_menu_week(query: CallbackQuery, callback_data: AdminMenuWeekCB):
    await query.message.edit_text(
        f"📝 <b>{callback_data.week}-hafta</b>\n\nKunni tanlang:",
        reply_markup=admin_menu_day_keyboard(callback_data.week),
    )
    await query.answer()


@router.callback_query(AdminMenuDayCB.filter(), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cb_admin_menu_day(query: CallbackQuery, callback_data: AdminMenuDayCB):
    item = await db.get_menu_item(callback_data.week, callback_data.day)
    m1 = item["meal_1"] if item else "—"
    m2 = item["meal_2"] if item else "—"
    text = (
        f"📝 <b>{callback_data.week}-hafta {callback_data.day}</b>\n\n"
        f"1-ovqat: {m1}\n"
        f"2-ovqat: {m2}"
    )
    await query.message.edit_text(
        text, reply_markup=admin_menu_day_detail_keyboard(callback_data.week, callback_data.day)
    )
    await query.answer()


@router.callback_query(AdminMenuEditStartCB.filter(), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cb_admin_menu_edit_start(query: CallbackQuery, callback_data: AdminMenuEditStartCB, state: FSMContext):
    await state.update_data(menu_week=callback_data.week, menu_day=callback_data.day)
    await state.set_state(AdminEdit.waiting_menu_day_text)
    await query.message.edit_text(
        f"✏️ <b>{callback_data.week}-hafta {callback_data.day}</b>\n\n"
        "Yangi taomlarni yuboring. Format:\n"
        "<code>1-ovqat nomi | 2-ovqat nomi</code>",
        reply_markup=admin_back_keyboard(),
    )
    await query.answer()


@router.message(AdminEdit.waiting_menu_day_text)
async def receive_menu_day_text(msg: Message, state: FSMContext):
    text = (msg.text or "").strip()
    if "|" not in text:
        await msg.answer("❌ '|' ajratuvchisi topilmadi. Format: <code>1-ovqat | 2-ovqat</code>")
        return

    data = await state.get_data()
    week = data.get("menu_week")
    day = data.get("menu_day")
    if not week or not day:
        await state.clear()
        await msg.answer("❌ Xatolik: qaysi kun ekani aniqlanmadi. /admin dan qaytadan urinib ko'ring.")
        return

    meal_1, meal_2 = [p.strip() for p in text.split("|", 1)]
    await db.update_menu_item(week, day, meal_1, meal_2)
    await state.clear()
    await msg.answer(f"✅ {week}-hafta {day} menyusi yangilandi.\n\n/admin — panelga qaytish")


# ── Sikl sozlash (bir bosishda) ──────────────────────────────────────────────

@router.callback_query(AdminCycleSetCB.filter(), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cb_admin_cycle_set(query: CallbackQuery, callback_data: AdminCycleSetCB):
    label_map = {(w, d): i for i, (w, d) in enumerate(CYCLE_LABELS)}
    idx = label_map.get((callback_data.week, callback_data.day))
    if idx is None:
        await query.answer("❌ Xatolik.", show_alert=True)
        return

    anchor_date = _today().isoformat()
    await db.update_cycle(anchor_date, callback_data.week, callback_data.day, idx)
    await query.message.edit_text(
        f"✅ <b>Sikl yangilandi!</b>\n\n"
        f"Bugun ({anchor_date}) = {callback_data.week}-hafta {callback_data.day}",
        reply_markup=admin_back_keyboard(),
    )
    await query.answer("✅ Saqlandi!")


async def _build_status_text() -> str:
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    from app.services.menu_service import get_menu_for_date
    from datetime import date as dt
    menu = await get_menu_for_date(dt.fromisoformat(tomorrow))

    users = await db.get_all_active_users()
    orders = await db.get_orders_for_date(tomorrow)
    order_map = {o["telegram_id"]: o for o in orders if o["is_confirmed"] == 1}

    confirmed, not_confirmed = [], []
    m1_yes, m1_no = [], []
    m2_yes, m2_no = [], []

    for u in users:
        tid = u["telegram_id"]
        o = order_map.get(tid)
        if not o:
            not_confirmed.append(u)
            continue
        confirmed.append(u)
        (m1_yes if o["meal_1_status"] == "yes" else m1_no).append(u)
        (m2_yes if o["meal_2_status"] == "yes" else m2_no).append(u)

    def nl(lst):
        return "\n".join(f"  {i+1}. {_dn(u)}" for i, u in enumerate(lst)) or "  —"

    menu_label = menu["week_label"] if menu else tomorrow
    m1_name = menu["meal_1"] if menu else "1-ovqat"
    m2_name = menu["meal_2"] if menu else "2-ovqat"

    parts = [
        f"📋 <b>Bugungi holat</b>",
        f"📅 {menu_label}\n",
        f"✅ Tasdiqlagan: {len(confirmed)} ta",
        f"⏳ Javob bermagan: {len(not_confirmed)} ta",
    ]
    if not_confirmed:
        parts.append(f"\n<b>Javob bermaganlar:</b>\n{nl(not_confirmed)}")

    parts += [
        f"\n━━━━━━━━━━━━━━━━",
        f"<b>1-ovqat:</b> {m1_name}",
        f"  Yeydi ({len(m1_yes)} ta): {', '.join(_dn(u) for u in m1_yes) or '—'}",
        f"  Yemaydi ({len(m1_no)} ta): {', '.join(_dn(u) for u in m1_no) or '—'}",
        f"\n<b>2-ovqat:</b> {m2_name}",
        f"  Yeydi ({len(m2_yes)} ta): {', '.join(_dn(u) for u in m2_yes) or '—'}",
        f"  Yemaydi ({len(m2_no)} ta): {', '.join(_dn(u) for u in m2_no) or '—'}",
    ]
    return "\n".join(parts)


async def _build_edit_list():
    """Barcha xodimlar va ularning ertangi buyurtma holati — tahrirlash uchun."""
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    from app.services.menu_service import get_menu_for_date
    from datetime import date as dt
    menu = await get_menu_for_date(dt.fromisoformat(tomorrow))

    users = await db.get_all_active_users()
    orders = await db.get_orders_for_date(tomorrow)
    order_map = {o["telegram_id"]: o for o in orders if o.get("is_confirmed")}

    menu_label = menu["week_label"] if menu else tomorrow
    m1_name = menu["meal_1"] if menu else "1-ovqat"
    m2_name = menu["meal_2"] if menu else "2-ovqat"

    lines = [
        "✏️ <b>Buyurtmalarni tahrirlash</b>",
        f"📅 {menu_label}",
        f"1-ovqat: {m1_name}",
        f"2-ovqat: {m2_name}\n",
        "Xodimni tanlang:",
    ]

    users_orders = [(u, order_map.get(u["telegram_id"])) for u in users]
    return "\n".join(lines), admin_edit_list_keyboard(users_orders)


async def _build_employees_text() -> str:
    users = await db.get_all_active_users()
    admins = [u for u in users if u.get("role") == "admin"]
    employees = [u for u in users if u.get("role") != "admin"]

    lines = [f"👥 <b>Xodimlar ro'yxati</b> (jami {len(users)} kishi)\n"]

    lines.append("<b>👑 Admin:</b>")
    for u in admins:
        nick = f"@{u['username']}" if u.get("username") else "username yo'q"
        started = "✅" if u.get("has_started") else "⭕"
        lines.append(f"  {started} {u.get('full_name', '—')} ({nick})")

    lines.append("\n<b>👤 Xodimlar:</b>")
    for i, u in enumerate(employees, 1):
        nick = f"@{u['username']}" if u.get("username") else "username yo'q"
        started = "✅" if u.get("has_started") else "⭕"
        name = u.get("full_name") or f"User_{u['telegram_id']}"
        lines.append(f"  {i}. {started} {name} ({nick})")

    lines.append("\n✅ = botga ulanganlar  |  ⭕ = hali ulanmaganlar")
    return "\n".join(lines)


# ── /set_users ────────────────────────────────────────────────────────────

@router.message(Command("set_users"), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cmd_set_users(msg: Message, state: FSMContext):
    await msg.answer(
        "Xodimlarning Telegram ID raqamlarini yuboring.\n"
        "Har bir ID ni yangi qatordan yozing.\n"
        "Jami 12 ta xodim ID yuborilishi kerak."
    )
    await state.set_state(AdminSetup.waiting_employees)


# ── /set_group ────────────────────────────────────────────────────────────

@router.message(Command("set_group"), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cmd_set_group(msg: Message, state: FSMContext):
    await msg.answer("Hisobot yuboriladigan guruh ID sini yuboring.")
    await state.set_state(AdminSetup.waiting_group)


# ── /set_menu ─────────────────────────────────────────────────────────────

@router.message(Command("set_menu"), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cmd_set_menu(msg: Message, state: FSMContext):
    await msg.answer(
        "Yangi menyu yuboring. Format:\n\n"
        "1-HAFTA\n"
        "Dushanba: 1-ovqat | 2-ovqat\n"
        "Seshanba: 1-ovqat | 2-ovqat\n"
        "...\n\n"
        "2-HAFTA\n"
        "Dushanba: 1-ovqat | 2-ovqat\n"
        "..."
    )
    await state.set_state(AdminSetup.waiting_menu)


@router.message(AdminSetup.waiting_menu)
async def receive_menu(msg: Message, state: FSMContext):
    text = msg.text.strip()
    current_week = None
    errors = []
    saved = 0

    day_names = {"Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"}

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("1-HAFTA"):
            current_week = 1
            continue
        if line.startswith("2-HAFTA"):
            current_week = 2
            continue
        if current_week and ":" in line:
            parts = line.split(":", 1)
            day = parts[0].strip()
            if day not in day_names:
                errors.append(f"Noma'lum kun: {day}")
                continue
            if "|" not in parts[1]:
                errors.append(f"'{day}' da '|' ajratuvchi yo'q")
                continue
            meals = parts[1].split("|", 1)
            await db.update_menu_item(current_week, day, meals[0].strip(), meals[1].strip())
            saved += 1

    await state.clear()
    if errors:
        await msg.answer(f"⚠️ {saved} ta saqlandi. Xatolar:\n" + "\n".join(errors))
    else:
        await msg.answer(f"✅ Menyu yangilandi! {saved} ta kun saqlandi.")


# ── /set_cycle ────────────────────────────────────────────────────────────

@router.message(Command("set_cycle"), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cmd_set_cycle(msg: Message):
    parts = msg.text.strip().split()
    if len(parts) != 4:
        await msg.answer(
            "Format: /set_cycle SANA HAFTA KUN\n"
            "Misol: /set_cycle 2026-06-21 1 Yakshanba\n\n"
            "HAFTA: 1 yoki 2\n"
            "KUN: Dushanba, Seshanba, Chorshanba, Payshanba, Juma, Shanba, Yakshanba"
        )
        return

    _, anchor_date_str, week_str, day_name = parts

    try:
        from datetime import date
        date.fromisoformat(anchor_date_str)
    except ValueError:
        await msg.answer("❌ Sana formati noto'g'ri. YYYY-MM-DD ko'rinishida yozing.")
        return

    try:
        week_number = int(week_str)
        assert week_number in (1, 2)
    except (ValueError, AssertionError):
        await msg.answer("❌ Hafta 1 yoki 2 bo'lishi kerak.")
        return

    label_map = {(w, d): i for i, (w, d) in enumerate(CYCLE_LABELS)}
    idx = label_map.get((week_number, day_name))
    if idx is None:
        await msg.answer(f"❌ '{day_name}' kun nomi noto'g'ri.")
        return

    await db.update_cycle(anchor_date_str, week_number, day_name, idx)
    await msg.answer(
        f"✅ Sikl yangilandi!\n"
        f"Boshlang'ich sana: {anchor_date_str}\n"
        f"Hafta: {week_number} | Kun: {day_name} | Indeks: {idx}"
    )


# ── /report ───────────────────────────────────────────────────────────────

@router.message(Command("report"), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cmd_report(msg: Message):
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    text = await build_order_report(tomorrow)
    await msg.answer(text)


# ── /today ────────────────────────────────────────────────────────────────

@router.message(Command("today"), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cmd_today(msg: Message):
    menu = await get_today_menu()
    if not menu:
        await msg.answer("Bugun uchun menyu topilmadi.")
        return
    await msg.answer(
        f"📅 Bugungi menyu — {menu['week_label']}\n\n"
        f"1-ovqat: {menu['meal_1']}\n"
        f"2-ovqat: {menu['meal_2']}"
    )


# ── /tomorrow ─────────────────────────────────────────────────────────────

@router.message(Command("tomorrow"), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cmd_tomorrow(msg: Message):
    menu = await get_tomorrow_menu()
    if not menu:
        await msg.answer("Ertaga uchun menyu topilmadi.")
        return
    await msg.answer(
        f"📅 Ertangi menyu — {menu['week_label']}\n\n"
        f"1-ovqat: {menu['meal_1']}\n"
        f"2-ovqat: {menu['meal_2']}"
    )


# ── /reset_day ────────────────────────────────────────────────────────────

@router.message(Command("reset_day"), F.from_user.func(lambda u: u.id in cfg.ADMIN_IDS))
async def cmd_reset_day(msg: Message):
    today = _today().isoformat()
    await db.reset_day_orders(today)
    await msg.answer(f"✅ {today} kuniga oid barcha buyurtmalar tozalandi.")
