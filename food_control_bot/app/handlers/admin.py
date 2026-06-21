import logging
from datetime import date
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import app.database as db
import app.config as cfg
from app.services.menu_service import (
    get_today_menu, get_tomorrow_menu, format_menu_text, CYCLE_LABELS
)
from app.services.report_service import build_order_report, build_final_report

log = logging.getLogger(__name__)
router = Router()


class AdminSetup(StatesGroup):
    waiting_employees = State()
    waiting_group     = State()
    waiting_menu      = State()


def is_admin_id(telegram_id: int) -> bool:
    return telegram_id == cfg.SUPER_ADMIN_ID


# ── /start ────────────────────────────────────────────────────────────────

@router.message(Command("start"), F.from_user.func(lambda u: u.id == cfg.SUPER_ADMIN_ID))
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
            "Mavjud buyruqlar:\n"
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

    # Admin o'zini ham qo'shadi
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
        "Bot tayyor. Har kuni 17:30 da ertangi taomnoma yuboriladi.\n"
        "22:00 da yakuniy hisobot guruhga va sizga yuboriladi."
    )


# ── /set_users ────────────────────────────────────────────────────────────

@router.message(Command("set_users"), F.from_user.func(lambda u: u.id == cfg.SUPER_ADMIN_ID))
async def cmd_set_users(msg: Message, state: FSMContext):
    await msg.answer(
        "Xodimlarning Telegram ID raqamlarini yuboring.\n"
        "Har bir ID ni yangi qatordan yozing.\n"
        "Jami 12 ta xodim ID yuborilishi kerak."
    )
    await state.set_state(AdminSetup.waiting_employees)


# ── /set_group ────────────────────────────────────────────────────────────

@router.message(Command("set_group"), F.from_user.func(lambda u: u.id == cfg.SUPER_ADMIN_ID))
async def cmd_set_group(msg: Message, state: FSMContext):
    await msg.answer("Hisobot yuboriladigan guruh ID sini yuboring.")
    await state.set_state(AdminSetup.waiting_group)


# ── /set_menu ─────────────────────────────────────────────────────────────

@router.message(Command("set_menu"), F.from_user.func(lambda u: u.id == cfg.SUPER_ADMIN_ID))
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

@router.message(Command("set_cycle"), F.from_user.func(lambda u: u.id == cfg.SUPER_ADMIN_ID))
async def cmd_set_cycle(msg: Message):
    """
    Misol: /set_cycle 2026-06-21 1 Yakshanba
    """
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

@router.message(Command("report"), F.from_user.func(lambda u: u.id == cfg.SUPER_ADMIN_ID))
async def cmd_report(msg: Message):
    from datetime import timedelta
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    text = await build_order_report(tomorrow)
    await msg.answer(text)


# ── /today ────────────────────────────────────────────────────────────────

@router.message(Command("today"), F.from_user.func(lambda u: u.id == cfg.SUPER_ADMIN_ID))
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

@router.message(Command("tomorrow"), F.from_user.func(lambda u: u.id == cfg.SUPER_ADMIN_ID))
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

@router.message(Command("reset_day"), F.from_user.func(lambda u: u.id == cfg.SUPER_ADMIN_ID))
async def cmd_reset_day(msg: Message):
    today = date.today().isoformat()
    await db.reset_day_orders(today)
    await msg.answer(f"✅ {today} kuniga oid barcha buyurtmalar tozalandi.")
