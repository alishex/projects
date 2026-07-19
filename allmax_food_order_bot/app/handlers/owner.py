import logging
import re
from datetime import date as date_cls, timedelta

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import app.config as cfg
import app.database as db
import app.scheduler as sched
from app.states import OwnerEdit
from app.keyboards import (
    OwnerPanelCB, OwnerDeptDetailCB, OwnerDeptAdminEditCB, OwnerDeptDeputyEditCB,
    OwnerDeptDeputyRemoveCB, OwnerDeptFixedToggleCB, OwnerDeptFixedEditCB,
    OwnerDeptDeleteCB, OwnerDeptAddCB, OwnerAddCB, OwnerRemoveCB, OwnerScheduleEditCB,
    OwnerOverridePickCB, OwnerMenuWeekCB, OwnerMenuDayCB, OwnerMenuEditStartCB, OwnerCycleSetCB,
    owner_main_keyboard, owner_back_keyboard, owner_status_keyboard, owner_override_pick_keyboard,
    owner_depts_keyboard, owner_dept_detail_keyboard, owner_owners_keyboard, owner_schedule_keyboard,
    owner_menu_week_keyboard, owner_menu_day_keyboard, owner_menu_day_detail_keyboard, owner_cycle_keyboard,
)

logger = logging.getLogger(__name__)
router = Router()


def _is_owner(user_id: int) -> bool:
    return user_id in cfg.OWNER_IDS


def _extract_id_from_message(msg: Message) -> "int | None":
    if msg.forward_from:
        return msg.forward_from.id
    text = (msg.text or "").strip()
    if text.lstrip("-").isdigit():
        return int(text)
    return None


def _parse_int(text: "str | None") -> "int | None":
    if not text:
        return None
    text = text.strip()
    try:
        val = int(text)
    except ValueError:
        return None
    return val if val >= 0 else None


def _tomorrow() -> str:
    return (date_cls.today() + timedelta(days=1)).isoformat()


def _slugify_key(name: str, existing_keys: set) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_") or "dept"
    key = base
    i = 2
    while key in existing_keys:
        key = f"{base}_{i}"
        i += 1
    return key


async def _guard_no_conflict(target: Message, state: FSMContext) -> bool:
    if await state.get_state() is not None:
        await target.answer("⚠️ Sizda tugallanmagan amal bor. Avval uni yakunlang yoki /cancel yozing.")
        return False
    return True


def _dept_detail_text(dept: dict) -> str:
    lines = [f"{dept['emoji']} <b>{dept['name']}</b>\n"]
    if dept.get("fixed_meal1") is not None:
        lines.append("Turkum: doimiy son (admin/so'rovsiz)")
        lines.append(f"Tushlik: <b>{dept['fixed_meal1']} ta</b> (doim)")
        lines.append(f"Kechki: <b>{dept['fixed_meal2']} ta</b> (doim)")
    else:
        admin_label = f"ID <code>{dept['admin_id']}</code>" if dept.get("admin_id") else "— tayinlanmagan"
        deputy_label = f"ID <code>{dept['deputy_id']}</code>" if dept.get("deputy_id") else "— yo'q"
        lines.append(f"Admin: {admin_label}")
        lines.append(f"O'rinbosar: {deputy_label}")
    return "\n".join(lines)


async def _build_status() -> tuple[str, list]:
    target_date = _tomorrow()
    orders = await db.get_orders_for_date(target_date)
    orders_by_key = {o["dept_key"]: o for o in orders}

    confirmed_lines = []
    pending_depts = []
    for d in cfg.DEPARTMENTS:
        o = orders_by_key.get(d["key"])
        if o and o.get("is_confirmed"):
            if o["admin_id"] == 0:
                who = "avtomatik"
            elif o["admin_id"] in cfg.OWNER_IDS:
                who = "owner"
            else:
                who = f"ID {o['admin_id']}"
            when = (o.get("updated_at") or "")[-8:-3]
            when_str = f", {when}" if when else ""
            confirmed_lines.append(f"{d['emoji']} {d['name']:<16} → {o['meal1_count']}/{o['meal2_count']}  ({who}{when_str})")
        else:
            pending_depts.append(d)

    pending_lines = []
    for d in pending_depts:
        bits = []
        if d.get("admin_id"):
            bits.append(f"admin {d['admin_id']}")
        if d.get("deputy_id"):
            bits.append(f"o'rinbosar {d['deputy_id']}")
        who = ", ".join(bits) if bits else "admin tayinlanmagan"
        pending_lines.append(f"{d['emoji']} {d['name']:<16} → {who}")

    text = (
        f"📊 <b>Ertangi holat</b>\n📅 {target_date}\n\n"
        f"✅ <b>Tasdiqlangan ({len(confirmed_lines)}/{len(cfg.DEPARTMENTS)}):</b>\n"
        + (f"<code>{chr(10).join(confirmed_lines)}</code>" if confirmed_lines else "  —")
        + "\n\n"
        f"⏳ <b>Javob bermagan ({len(pending_lines)}):</b>\n"
        + (f"<code>{chr(10).join(pending_lines)}</code>" if pending_lines else "  —")
    )
    return text, pending_depts


# ── Kirish nuqtalari ─────────────────────────────────────────────────────────

@router.message(Command("start"), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def owner_start(message: Message):
    await message.answer(
        "👋 Xush kelibsiz, siz <b>owner</b> sifatida ro'yxatdan o'tgansiz.\n\n"
        "/owner — Owner panelni ochish",
        parse_mode="HTML"
    )


@router.message(Command("start"))
async def owner_start_fallback(message: Message):
    # Bu yerga faqat na bo'lim admin/o'rinbosari, na owner bo'lgan odam yetib
    # keladi (admin.router va yuqoridagi owner_start filtrlaridan o'tolmasa).
    await message.answer("Sizda ruxsat yo'q.")


@router.message(Command("owner"), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cmd_owner(message: Message):
    await message.answer(
        "👑 <b>Owner Panel</b>\n\nQuyidagi bo'limlardan birini tanlang:",
        parse_mode="HTML", reply_markup=owner_main_keyboard()
    )


@router.message(Command("owner"))
async def cmd_owner_fallback(message: Message):
    await message.answer("Sizda ruxsat yo'q.")


@router.message(Command("cancel"), StateFilter("*"), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def owner_cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.")


# ── Asosiy panel navigatsiyasi ────────────────────────────────────────────────

@router.callback_query(OwnerPanelCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_owner_panel(query: CallbackQuery, callback_data: OwnerPanelCB):
    section = callback_data.section

    if section == "main":
        await query.message.edit_text(
            "👑 <b>Owner Panel</b>\n\nQuyidagi bo'limlardan birini tanlang:",
            parse_mode="HTML", reply_markup=owner_main_keyboard()
        )

    elif section == "status":
        text, pending = await _build_status()
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=owner_status_keyboard(pending))

    elif section == "override_pick":
        depts = [d for d in cfg.DEPARTMENTS if d.get("fixed_meal1") is None]
        await query.message.edit_text(
            "✏️ <b>Buyurtma kiritish (o'rniga)</b>\n\nQaysi bo'lim uchun kiritasiz?",
            parse_mode="HTML", reply_markup=owner_override_pick_keyboard(depts)
        )

    elif section == "depts":
        await query.message.edit_text(
            f"🏢 <b>Bo'limlar</b> (jami {len(cfg.DEPARTMENTS)} ta)\n\nBoshqarish uchun bo'limni tanlang:",
            parse_mode="HTML", reply_markup=owner_depts_keyboard(cfg.DEPARTMENTS)
        )

    elif section == "owners":
        owners = await db.get_owners()
        lines = "\n".join(f"  👑 {o.get('full_name') or o['telegram_id']} (ID: <code>{o['telegram_id']}</code>)" for o in owners)
        await query.message.edit_text(
            f"👑 <b>Ownerlar</b> (jami {len(owners)} kishi)\n\n{lines}",
            parse_mode="HTML", reply_markup=owner_owners_keyboard(owners)
        )

    elif section == "schedule":
        settings = await db.get_settings()
        poll_t = (settings or {}).get("poll_time") or cfg.DEFAULT_POLL_TIME
        report_t = (settings or {}).get("report_time") or cfg.DEFAULT_REPORT_TIME
        await query.message.edit_text(
            f"🕐 <b>Vaqtlar</b>\n\nSo'rov yuborish: <code>{poll_t}</code>\nHisobot: <code>{report_t}</code>\n\n"
            f"O'zgartirish uchun tugmani bosing.",
            parse_mode="HTML", reply_markup=owner_schedule_keyboard()
        )

    elif section == "menu_edit":
        await query.message.edit_text(
            "📝 <b>Menyu</b>\n\nHaftani tanlang:", parse_mode="HTML", reply_markup=owner_menu_week_keyboard()
        )

    elif section == "cycle":
        await query.message.edit_text(
            "🔄 <b>Sikl sozlash</b>\n\nBugun aslida qaysi hafta/kun bo'lishi kerakligini tanlang:",
            parse_mode="HTML", reply_markup=owner_cycle_keyboard()
        )

    elif section == "report_now":
        # Kunlik avtomatik hisobotni (odatda belgilangan vaqtda, standart 18:00)
        # kutmasdan hozir olish — bir xil sched.send_owner_report funksiyasi
        # ishlatiladi, shuning uchun format/qabul qiluvchilar avtomatik
        # postdan farq qilmaydi.
        await sched.send_owner_report(query.bot)
        await query.answer("✅ Hisobot yuborildi!")
        return

    await query.answer()


# ── Adminlar o'rniga buyurtma kiritish ────────────────────────────────────────

@router.callback_query(OwnerOverridePickCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_override_pick(query: CallbackQuery, callback_data: OwnerOverridePickCB, state: FSMContext):
    dept = cfg.DEPT_BY_KEY.get(callback_data.dept_key)
    if dept is None:
        await query.answer("❌ Bo'lim topilmadi.", show_alert=True)
        return
    if not await _guard_no_conflict(query.message, state):
        await query.answer()
        return

    target_date = _tomorrow()
    from app.services.menu_service import get_menu_for_date
    menu = await get_menu_for_date(date_cls.fromisoformat(target_date))
    m1_name = menu["meal_1"] if menu else "—"
    m2_name = menu["meal_2"] if menu else "—"

    await state.set_state(OwnerEdit.waiting_override_meal1)
    await state.update_data(dept_key=dept["key"], target_date=target_date, meal1_name=m1_name, meal2_name=m2_name)
    await query.message.edit_text(
        f"✏️ <b>{dept['emoji']} {dept['name']}</b> o'rniga kiritish\n📅 {target_date}\n\n"
        f"🥘 <b>Tushlik:</b> {m1_name}\n\nNechta porsiya?\n<i>(Faqat raqam kiriting)</i>",
        parse_mode="HTML"
    )
    await query.answer()


@router.message(OwnerEdit.waiting_override_meal1, F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def owner_override_meal1(message: Message, state: FSMContext):
    count = _parse_int(message.text)
    if count is None:
        await message.answer("❌ Faqat son kiriting!")
        return
    data = await state.get_data()
    await state.update_data(meal1_count=count)
    await state.set_state(OwnerEdit.waiting_override_meal2)
    await message.answer(
        f"✅ Tushlik: <b>{count} ta</b>\n\n🌙 <b>Kechki:</b> {data['meal2_name']}\n\nNechta porsiya?",
        parse_mode="HTML"
    )


@router.message(OwnerEdit.waiting_override_meal2, F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def owner_override_meal2(message: Message, state: FSMContext):
    count = _parse_int(message.text)
    if count is None:
        await message.answer("❌ Faqat son kiriting!")
        return
    data = await state.get_data()
    dept = cfg.DEPT_BY_KEY.get(data.get("dept_key"))
    await state.clear()
    if dept is None:
        await message.answer("❌ Xatolik: bo'lim topilmadi.")
        return

    await db.upsert_order(
        date_str=data["target_date"], dept_key=dept["key"], admin_id=message.from_user.id,
        meal1_count=data["meal1_count"], meal2_count=count, confirmed=True
    )
    await message.answer(
        f"✅ <b>{dept['emoji']} {dept['name']}</b> uchun kiritildi (owner tomonidan):\n\n"
        f"🥘 Tushlik: <b>{data['meal1_count']} ta</b>\n🌙 Kechki: <b>{count} ta</b>\n\n/owner — panelga qaytish",
        parse_mode="HTML"
    )
    logger.info(f"Owner override: dept={dept['key']} date={data['target_date']} "
                f"m1={data['meal1_count']} m2={count} by={message.from_user.id}")


# ── Bo'limlarni boshqarish ───────────────────────────────────────────────────

@router.callback_query(OwnerDeptDetailCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_dept_detail(query: CallbackQuery, callback_data: OwnerDeptDetailCB):
    dept = cfg.DEPT_BY_KEY.get(callback_data.dept_key)
    if dept is None:
        await query.answer("❌ Bo'lim topilmadi.", show_alert=True)
        return
    await query.message.edit_text(_dept_detail_text(dept), parse_mode="HTML", reply_markup=owner_dept_detail_keyboard(dept))
    await query.answer()


@router.callback_query(OwnerDeptAdminEditCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_dept_admin_edit(query: CallbackQuery, callback_data: OwnerDeptAdminEditCB, state: FSMContext):
    dept = cfg.DEPT_BY_KEY.get(callback_data.dept_key)
    if dept is None:
        await query.answer("❌ Bo'lim topilmadi.", show_alert=True)
        return
    if not await _guard_no_conflict(query.message, state):
        await query.answer()
        return
    await state.set_state(OwnerEdit.waiting_dept_admin_id)
    await state.update_data(dept_key=dept["key"])
    await query.message.edit_text(
        f"✏️ <b>{dept['emoji']} {dept['name']}</b> uchun yangi admin\n\nTelegram ID yuboring yoki xabarni forward qiling.",
        parse_mode="HTML", reply_markup=owner_back_keyboard()
    )
    await query.answer()


@router.message(OwnerEdit.waiting_dept_admin_id, F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def owner_receive_dept_admin(message: Message, state: FSMContext):
    tid = _extract_id_from_message(message)
    if tid is None:
        await message.answer("❌ ID topilmadi. Raqam yuboring yoki xabarni forward qiling.")
        return
    data = await state.get_data()
    dept = cfg.DEPT_BY_KEY.get(data.get("dept_key"))
    await state.clear()
    if dept is None:
        await message.answer("❌ Xatolik: bo'lim topilmadi.")
        return
    await db.set_department_admin(dept["key"], tid)
    await db.refresh_runtime_config()
    await message.answer(
        f"✅ {dept['emoji']} {dept['name']} admini yangilandi (ID: <code>{tid}</code>).\n\n/owner — panelga qaytish",
        parse_mode="HTML"
    )


@router.callback_query(OwnerDeptDeputyEditCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_dept_deputy_edit(query: CallbackQuery, callback_data: OwnerDeptDeputyEditCB, state: FSMContext):
    dept = cfg.DEPT_BY_KEY.get(callback_data.dept_key)
    if dept is None:
        await query.answer("❌ Bo'lim topilmadi.", show_alert=True)
        return
    if not await _guard_no_conflict(query.message, state):
        await query.answer()
        return
    await state.set_state(OwnerEdit.waiting_dept_deputy_id)
    await state.update_data(dept_key=dept["key"])
    await query.message.edit_text(
        f"✏️ <b>{dept['emoji']} {dept['name']}</b> uchun o'rinbosar\n\nTelegram ID yuboring yoki xabarni forward qiling.",
        parse_mode="HTML", reply_markup=owner_back_keyboard()
    )
    await query.answer()


@router.message(OwnerEdit.waiting_dept_deputy_id, F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def owner_receive_dept_deputy(message: Message, state: FSMContext):
    tid = _extract_id_from_message(message)
    if tid is None:
        await message.answer("❌ ID topilmadi. Raqam yuboring yoki xabarni forward qiling.")
        return
    data = await state.get_data()
    dept = cfg.DEPT_BY_KEY.get(data.get("dept_key"))
    await state.clear()
    if dept is None:
        await message.answer("❌ Xatolik: bo'lim topilmadi.")
        return
    await db.set_department_deputy(dept["key"], tid)
    await db.refresh_runtime_config()
    await message.answer(
        f"✅ {dept['emoji']} {dept['name']} o'rinbosari yangilandi (ID: <code>{tid}</code>).\n\n/owner — panelga qaytish",
        parse_mode="HTML"
    )


@router.callback_query(OwnerDeptDeputyRemoveCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_dept_deputy_remove(query: CallbackQuery, callback_data: OwnerDeptDeputyRemoveCB):
    dept = cfg.DEPT_BY_KEY.get(callback_data.dept_key)
    if dept is None:
        await query.answer("❌ Bo'lim topilmadi.", show_alert=True)
        return
    await db.set_department_deputy(dept["key"], None)
    await db.refresh_runtime_config()
    dept = cfg.DEPT_BY_KEY.get(callback_data.dept_key)
    await query.message.edit_text(_dept_detail_text(dept), parse_mode="HTML", reply_markup=owner_dept_detail_keyboard(dept))
    await query.answer("✅ O'rinbosar olib tashlandi.")


@router.callback_query(OwnerDeptFixedToggleCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_dept_fixed_toggle(query: CallbackQuery, callback_data: OwnerDeptFixedToggleCB):
    dept = cfg.DEPT_BY_KEY.get(callback_data.dept_key)
    if dept is None:
        await query.answer("❌ Bo'lim topilmadi.", show_alert=True)
        return
    if callback_data.to_fixed:
        await db.set_department_fixed(dept["key"], 0, 0)
    else:
        await db.set_department_fixed(dept["key"], None, None)
    await db.refresh_runtime_config()
    dept = cfg.DEPT_BY_KEY.get(callback_data.dept_key)
    await query.message.edit_text(_dept_detail_text(dept), parse_mode="HTML", reply_markup=owner_dept_detail_keyboard(dept))
    await query.answer("✅ Yangilandi.")


@router.callback_query(OwnerDeptFixedEditCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_dept_fixed_edit(query: CallbackQuery, callback_data: OwnerDeptFixedEditCB, state: FSMContext):
    dept = cfg.DEPT_BY_KEY.get(callback_data.dept_key)
    if dept is None:
        await query.answer("❌ Bo'lim topilmadi.", show_alert=True)
        return
    if not await _guard_no_conflict(query.message, state):
        await query.answer()
        return
    await state.set_state(OwnerEdit.waiting_fixed_value)
    await state.update_data(dept_key=dept["key"], meal=callback_data.meal)
    label = "Tushlik" if callback_data.meal == 1 else "Kechki"
    await query.message.edit_text(
        f"✏️ {dept['emoji']} {dept['name']} — {label} doimiy soni\n\nYangi sonni kiriting:",
        reply_markup=owner_back_keyboard()
    )
    await query.answer()


@router.message(OwnerEdit.waiting_fixed_value, F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def owner_receive_fixed_value(message: Message, state: FSMContext):
    count = _parse_int(message.text)
    if count is None:
        await message.answer("❌ Faqat son kiriting!")
        return
    data = await state.get_data()
    dept = cfg.DEPT_BY_KEY.get(data.get("dept_key"))
    await state.clear()
    if dept is None:
        await message.answer("❌ Xatolik: bo'lim topilmadi.")
        return
    m1 = count if data["meal"] == 1 else (dept.get("fixed_meal1") or 0)
    m2 = count if data["meal"] == 2 else (dept.get("fixed_meal2") or 0)
    await db.set_department_fixed(dept["key"], m1, m2)
    await db.refresh_runtime_config()
    await message.answer(f"✅ {dept['emoji']} {dept['name']} yangilandi: {m1}/{m2}\n\n/owner — panelga qaytish")


@router.callback_query(OwnerDeptDeleteCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_dept_delete(query: CallbackQuery, callback_data: OwnerDeptDeleteCB):
    dept = cfg.DEPT_BY_KEY.get(callback_data.dept_key)
    if dept is None:
        await query.answer("❌ Bo'lim topilmadi.", show_alert=True)
        return
    await db.delete_department(dept["key"])
    await db.refresh_runtime_config()
    await query.message.edit_text(
        f"🏢 <b>Bo'limlar</b> (jami {len(cfg.DEPARTMENTS)} ta)\n\nBoshqarish uchun bo'limni tanlang:",
        parse_mode="HTML", reply_markup=owner_depts_keyboard(cfg.DEPARTMENTS)
    )
    await query.answer(f"✅ {dept['name']} o'chirildi.")


@router.callback_query(OwnerDeptAddCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_dept_add(query: CallbackQuery, state: FSMContext):
    if not await _guard_no_conflict(query.message, state):
        await query.answer()
        return
    await state.set_state(OwnerEdit.waiting_new_dept_name)
    await query.message.edit_text(
        "➕ <b>Yangi bo'lim</b>\n\nBo'lim nomini kiriting (masalan: Xavfsizlik):",
        parse_mode="HTML", reply_markup=owner_back_keyboard()
    )
    await query.answer()


@router.message(OwnerEdit.waiting_new_dept_name, F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def owner_receive_dept_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer("❌ Bo'sh nom bo'lishi mumkin emas. Qaytadan kiriting:")
        return
    await state.update_data(new_dept_name=name)
    await state.set_state(OwnerEdit.waiting_new_dept_emoji)
    await message.answer("Endi bo'lim uchun bitta emoji yuboring (masalan: 🛡):")


@router.message(OwnerEdit.waiting_new_dept_emoji, F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def owner_receive_dept_emoji(message: Message, state: FSMContext):
    emoji = (message.text or "").strip()
    if not emoji:
        await message.answer("❌ Bo'sh bo'lishi mumkin emas. Emoji yuboring:")
        return
    data = await state.get_data()
    name = data["new_dept_name"]
    await state.clear()

    existing_keys = {d["key"] for d in cfg.DEPARTMENTS}
    key = _slugify_key(name, existing_keys)
    await db.add_department(key, name, emoji[:8])
    await db.refresh_runtime_config()
    await message.answer(
        f"✅ Yangi bo'lim qo'shildi: {emoji[:8]} {name}\n\n"
        f"Endi admin tayinlash uchun 🏢 Bo'limlar bo'limidan uni tanlang.\n\n/owner — panelga qaytish"
    )


# ── Ownerlarni boshqarish ────────────────────────────────────────────────────

@router.callback_query(OwnerAddCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_owner_add(query: CallbackQuery, state: FSMContext):
    if not await _guard_no_conflict(query.message, state):
        await query.answer()
        return
    await state.set_state(OwnerEdit.waiting_owner_id)
    await query.message.edit_text(
        "➕ <b>Owner qo'shish</b>\n\nTelegram ID yuboring yoki xabarni forward qiling.",
        parse_mode="HTML", reply_markup=owner_back_keyboard()
    )
    await query.answer()


@router.message(OwnerEdit.waiting_owner_id, F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def owner_receive_new_owner(message: Message, state: FSMContext):
    tid = _extract_id_from_message(message)
    if tid is None:
        await message.answer("❌ ID topilmadi. Raqam yuboring yoki xabarni forward qiling.")
        return
    name = message.forward_from.full_name if message.forward_from else None
    await state.clear()
    await db.add_owner(tid, name)
    await db.refresh_runtime_config()
    await message.answer(f"✅ Yangi owner qo'shildi (ID: <code>{tid}</code>).\n\n/owner — panelga qaytish", parse_mode="HTML")


@router.callback_query(OwnerRemoveCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_owner_remove(query: CallbackQuery, callback_data: OwnerRemoveCB):
    owners = await db.get_owners()
    if len(owners) <= 1:
        await query.answer("❌ Kamida bitta owner qolishi shart.", show_alert=True)
        return
    await db.remove_owner(callback_data.telegram_id)
    await db.refresh_runtime_config()
    owners = await db.get_owners()
    lines = "\n".join(f"  👑 {o.get('full_name') or o['telegram_id']} (ID: <code>{o['telegram_id']}</code>)" for o in owners)
    await query.message.edit_text(
        f"👑 <b>Ownerlar</b> (jami {len(owners)} kishi)\n\n{lines}",
        parse_mode="HTML", reply_markup=owner_owners_keyboard(owners)
    )
    await query.answer("✅ Owner olib tashlandi.")


# ── Vaqtlarni sozlash ────────────────────────────────────────────────────────

@router.callback_query(OwnerScheduleEditCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_schedule_edit(query: CallbackQuery, callback_data: OwnerScheduleEditCB, state: FSMContext):
    if not await _guard_no_conflict(query.message, state):
        await query.answer()
        return
    await state.update_data(schedule_field=callback_data.field)
    await state.set_state(OwnerEdit.waiting_schedule_time)
    label = "So'rov yuborish" if callback_data.field == "poll" else "Hisobot"
    await query.message.edit_text(
        f"✏️ <b>{label} vaqti</b>\n\nYangi vaqtni HH:MM formatida yuboring (masalan: 17:30).",
        parse_mode="HTML", reply_markup=owner_back_keyboard()
    )
    await query.answer()


@router.message(OwnerEdit.waiting_schedule_time, F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def owner_receive_schedule_time(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    try:
        hh_str, mm_str = text.split(":")
        hh, mm = int(hh_str), int(mm_str)
        assert 0 <= hh <= 23 and 0 <= mm <= 59
    except (ValueError, AssertionError):
        await message.answer("❌ Format noto'g'ri. HH:MM ko'rinishida yuboring (masalan: 17:30).")
        return

    data = await state.get_data()
    field = data.get("schedule_field")
    await state.clear()

    if field == "poll":
        await sched.reschedule_poll_time(hh, mm)
        await message.answer(f"✅ So'rov yuborish vaqti <code>{hh:02d}:{mm:02d}</code> ga o'zgartirildi.\n\n/owner", parse_mode="HTML")
    elif field == "report":
        await sched.reschedule_report_time(hh, mm)
        await message.answer(f"✅ Hisobot vaqti <code>{hh:02d}:{mm:02d}</code> ga o'zgartirildi.\n\n/owner", parse_mode="HTML")
    else:
        await message.answer("❌ Xatolik: qaysi vaqt ekani aniqlanmadi. /owner dan qaytadan urinib ko'ring.")


# ── Menyu tahrirlash (tugmali) ────────────────────────────────────────────────

@router.callback_query(OwnerMenuWeekCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_menu_week(query: CallbackQuery, callback_data: OwnerMenuWeekCB):
    await query.message.edit_text(
        f"📝 <b>{callback_data.week}-hafta</b>\n\nKunni tanlang:",
        parse_mode="HTML", reply_markup=owner_menu_day_keyboard(callback_data.week)
    )
    await query.answer()


@router.callback_query(OwnerMenuDayCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_menu_day(query: CallbackQuery, callback_data: OwnerMenuDayCB):
    item = await db.get_menu_item(callback_data.week, callback_data.day)
    m1 = item["meal_1"] if item else "—"
    m2 = item["meal_2"] if item else "—"
    text = f"📝 <b>{callback_data.week}-hafta {callback_data.day}</b>\n\n1-ovqat: {m1}\n2-ovqat: {m2}"
    await query.message.edit_text(
        text, parse_mode="HTML", reply_markup=owner_menu_day_detail_keyboard(callback_data.week, callback_data.day)
    )
    await query.answer()


@router.callback_query(OwnerMenuEditStartCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_menu_edit_start(query: CallbackQuery, callback_data: OwnerMenuEditStartCB, state: FSMContext):
    if not await _guard_no_conflict(query.message, state):
        await query.answer()
        return
    await state.update_data(menu_week=callback_data.week, menu_day=callback_data.day)
    await state.set_state(OwnerEdit.waiting_menu_day_text)
    await query.message.edit_text(
        f"✏️ <b>{callback_data.week}-hafta {callback_data.day}</b>\n\n"
        f"Yangi taomlarni yuboring. Format:\n<code>1-ovqat nomi | 2-ovqat nomi</code>",
        parse_mode="HTML", reply_markup=owner_back_keyboard()
    )
    await query.answer()


@router.message(OwnerEdit.waiting_menu_day_text, F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def owner_receive_menu_day_text(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if "|" not in text:
        await message.answer("❌ '|' ajratuvchisi topilmadi. Format: <code>1-ovqat | 2-ovqat</code>", parse_mode="HTML")
        return

    data = await state.get_data()
    week = data.get("menu_week")
    day = data.get("menu_day")
    if not week or not day:
        await state.clear()
        await message.answer("❌ Xatolik: qaysi kun ekani aniqlanmadi. /owner dan qaytadan urinib ko'ring.")
        return

    meal_1, meal_2 = [p.strip() for p in text.split("|", 1)]
    await db.update_menu_item(week, day, meal_1, meal_2)
    await state.clear()
    await message.answer(f"✅ {week}-hafta {day} menyusi yangilandi.\n\n/owner — panelga qaytish")


# ── Sikl sozlash (bir bosishda) ───────────────────────────────────────────────

@router.callback_query(OwnerCycleSetCB.filter(), F.from_user.func(lambda u: u.id in cfg.OWNER_IDS))
async def cb_cycle_set(query: CallbackQuery, callback_data: OwnerCycleSetCB):
    from app.services.menu_service import CYCLE_LABELS
    label_map = {(w, d): i for i, (w, d) in enumerate(CYCLE_LABELS)}
    idx = label_map.get((callback_data.week, callback_data.day))
    if idx is None:
        await query.answer("❌ Xatolik.", show_alert=True)
        return

    anchor_date = date_cls.today().isoformat()
    await db.update_cycle(anchor_date, idx)
    await query.message.edit_text(
        f"✅ <b>Sikl yangilandi!</b>\n\nBugun ({anchor_date}) = {callback_data.week}-hafta {callback_data.day}",
        parse_mode="HTML", reply_markup=owner_back_keyboard()
    )
    await query.answer("✅ Saqlandi!")
