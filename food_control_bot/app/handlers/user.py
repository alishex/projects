import logging
from app.utils import today as _today
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

import app.database as db
import app.config as cfg
from app.keyboards import main_reply_keyboard, report_meal_keyboard
from app.handlers.callbacks import UserState

log = logging.getLogger(__name__)
router = Router()


def _mention(user) -> str:
    if user.username:
        return f"@{user.username}"
    return f'<a href="tg://user?id={user.id}">{user.full_name}</a>'


# ── /start (foydalanuvchi) ────────────────────────────────────────────────

@router.message(Command("start"))
async def user_start(msg: Message):
    tid = msg.from_user.id

    # Admin o'zini qayta qo'shmasin (admin handleri oldin ishlaganida qaytib keladi)
    if tid == cfg.SUPER_ADMIN_ID:
        return

    user = await db.get_user(tid)
    if not user:
        await msg.answer("Siz ushbu botdan foydalanish huquqiga ega emassiz.")
        return

    await db.update_user_started(
        telegram_id=tid,
        full_name=msg.from_user.full_name,
        username=msg.from_user.username,
    )
    await msg.answer(
        "Salom! Siz ovqat nazorati botiga ulandingiz.",
        reply_markup=main_reply_keyboard(),
    )


# ── "Ovqat hisoboti" tugmasi ──────────────────────────────────────────────

@router.message(F.text == "🍽 Ovqat hisoboti")
async def handle_food_report_btn(msg: Message, state: FSMContext):
    tid = msg.from_user.id
    user = await db.get_user(tid)
    if not user:
        await msg.answer("Siz ushbu botdan foydalanish huquqiga ega emassiz.")
        return

    await msg.answer(
        "Qaysi ovqatni yeb tugatdingiz?",
        reply_markup=report_meal_keyboard(),
    )


# ── Round video (ovqat hisoboti) ──────────────────────────────────────────

@router.message(UserState.waiting_video, F.video_note)
async def handle_video_report(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    meal_num = data.get("report_meal")
    today = data.get("report_date", _today().isoformat())
    tid = msg.from_user.id

    if not meal_num:
        await state.clear()
        return

    video_file_id = msg.video_note.file_id

    await db.save_meal_report(today, tid, meal_num, video_file_id)
    await state.clear()

    # Xodim maʼlumotlari
    user = await db.get_user(tid)
    display_name = f"@{user['username']}" if user and user.get("username") else (
        user.get("full_name", f"User_{tid}") if user else f"User_{tid}"
    )

    # Menyu nomi
    from app.services.menu_service import get_today_menu
    menu = await get_today_menu()
    meal_name = ""
    if menu:
        meal_name = menu["meal_1"] if meal_num == 1 else menu["meal_2"]

    # Admin mention
    settings = await db.get_settings()
    admin_id = settings.get("admin_id") if settings else cfg.SUPER_ADMIN_ID
    admin_user = await db.get_user(admin_id) if admin_id else None
    if admin_user and admin_user.get("username"):
        admin_mention = f"@{admin_user['username']}"
    else:
        admin_mention = f'<a href="tg://user?id={admin_id}">Admin</a>'

    caption = (
        f"🍽 Ovqat hisoboti\n\n"
        f"Xodim: {display_name}\n"
        f"Ovqat: {meal_num}-ovqat — {meal_name}\n\n"
        f"Admin: {admin_mention}"
    )

    # Adminga yuborish
    if admin_id:
        try:
            await bot.send_message(admin_id, caption)
            await bot.send_video_note(admin_id, video_file_id)
        except Exception as e:
            log.warning("Admin ga video yubora olmadim: %s", e)

    # Guruhga yuborish
    group_id = settings.get("group_id") if settings else None
    if group_id:
        try:
            await bot.send_message(group_id, caption)
            await bot.send_video_note(group_id, video_file_id)
        except Exception as e:
            log.warning("Guruhga video yubora olmadim: %s", e)

    await msg.answer(
        "✅ Hisobotingiz qabul qilindi va yuborildi!",
        reply_markup=main_reply_keyboard(),
    )


# ── Noto'g'ri fayl turing (waiting_video holatida) ───────────────────────

@router.message(UserState.waiting_video, ~F.video_note)
async def wrong_media_type(msg: Message):
    await msg.answer(
        "Iltimos, oddiy video yoki rasm emas, round video yuboring.\n"
        "(Telegram kamerasidagi doira tugmasidan olingan video)"
    )


# ── Ro'yxatda bo'lmagan foydalanuvchi ─────────────────────────────────────

@router.message(F.text & ~F.text.startswith("/"))
async def unregistered_text(msg: Message):
    if msg.from_user.id == cfg.SUPER_ADMIN_ID:
        return
    user = await db.get_user(msg.from_user.id)
    if not user:
        await msg.answer("Siz ushbu botdan foydalanish huquqiga ega emassiz.")
