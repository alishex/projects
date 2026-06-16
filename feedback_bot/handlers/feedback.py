import asyncio
import json
import logging
import os
from datetime import datetime

from aiogram import Router, F
from aiogram.types import ReplyKeyboardRemove
from aiogram.types import Message, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.context import FSMContext

from states import FeedbackStates
from keyboards.rating import rating_kb, phone_kb
from keyboards.menu import main_menu
from config import ADMIN_CHAT_ID

logger = logging.getLogger(__name__)
router = Router()
STORAGE_PATH = "storage/feedbacks.json"
_store_lock = asyncio.Lock()

MAX_TEXT_HISTORY = 50
MAX_MEDIA_HISTORY = 10


def ensure_storage():
    os.makedirs("storage", exist_ok=True)
    if not os.path.exists(STORAGE_PATH):
        with open(STORAGE_PATH, "w", encoding="utf-8") as f:
            f.write("{}")


def load_store() -> dict:
    ensure_storage()
    try:
        with open(STORAGE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.error("feedbacks.json o'qishda xato: %s", exc)
        return {}


def save_store(store: dict):
    ensure_storage()
    tmp = STORAGE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STORAGE_PATH)


def normalize_user(user: dict) -> dict:
    user = user or {}
    user.setdefault("full_name", "—")
    user.setdefault("username", None)
    user.setdefault("phone", None)
    user.setdefault("last_rating", None)
    user.setdefault("comments", [])
    user.setdefault("media", [])
    user.setdefault("group_message_ids", [])

    if "group_message_id" in user and isinstance(user.get("group_message_ids"), list) and not user["group_message_ids"]:
        old_one = user.get("group_message_id")
        user["group_message_ids"] = [old_one] if old_one else []
        user.pop("group_message_id", None)

    if not isinstance(user["comments"], list):
        user["comments"] = []
    if not isinstance(user["media"], list):
        user["media"] = []
    if not isinstance(user["group_message_ids"], list):
        user["group_message_ids"] = []

    return user


def trim_history(user: dict):
    user["comments"] = user["comments"][-MAX_TEXT_HISTORY:]
    user["media"] = user["media"][-MAX_MEDIA_HISTORY:]


def build_text(uid: str, u: dict) -> str:
    username = u.get("username") or "—"
    phone = u.get("phone") or "Kiritilmagan"
    rating = u.get("last_rating") or "—"

    lines = [
        "🆕 Mijoz fikrlari (xarid jarayoni)",
        "",
        f"👤 Mijoz: {u.get('full_name')} (@{username})",
        f"🆔 ID: {uid}",
        f"⭐ So'nggi baho: {rating}",
        f"📞 Aloqa: {phone}",
        "",
        "📝 Fikrlar:"
    ]

    if u["comments"]:
        for i, c in enumerate(u["comments"], 1):
            lines.append(f"\n{i}) {c['text']}\n   ⏱ {c['date']}")
    else:
        lines.append("—")

    if u["media"]:
        lines.append("")
        lines.append("📎 Media va ovozli fayllar ushbu xabar ostida yuboriladi.")

    return "\n".join(lines)


async def delete_old_package(bot, chat_id: int, message_ids: list[int]):
    for mid in message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception as exc:
            logger.debug("Eski xabar o'chirilmadi (mid=%s): %s", mid, exc)


async def send_package(bot, chat_id: int, summary_text: str, media_items: list[dict]) -> list[int]:
    sent_ids: list[int] = []

    try:
        msg = await bot.send_message(chat_id, summary_text)
        sent_ids.append(msg.message_id)
    except Exception as exc:
        logger.error("Admin guruhga matn yuborishda xato (chat_id=%s): %s", chat_id, exc)
        return sent_ids

    if not media_items:
        return sent_ids

    group = []
    for m in media_items:
        t = m.get("type")
        fid = m.get("file_id")
        if not fid:
            continue
        if t == "photo":
            group.append(InputMediaPhoto(media=fid))
        elif t == "video":
            group.append(InputMediaVideo(media=fid))

    group = group[:10]
    if group:
        try:
            msgs = await bot.send_media_group(chat_id, group)
            sent_ids.extend([m.message_id for m in msgs])
        except Exception as exc:
            logger.error("Media group yuborishda xato: %s", exc)

    for m in media_items:
        if m.get("type") == "video_note" and m.get("file_id"):
            try:
                vn = await bot.send_video_note(chat_id, m["file_id"])
                sent_ids.append(vn.message_id)
            except Exception as exc:
                logger.error("Video note yuborishda xato: %s", exc)
        elif m.get("type") == "voice" and m.get("file_id"):
            try:
                vo = await bot.send_voice(chat_id, m["file_id"])
                sent_ids.append(vo.message_id)
            except Exception as exc:
                logger.error("Voice yuborishda xato: %s", exc)

    return sent_ids


@router.message(F.text == "📝 Fikr qoldirish")
async def ask_feedback(message: Message, state: FSMContext):
    await state.set_state(FeedbackStates.waiting_feedback_text)
    await message.answer(
        "Fikringizni batafsil yozib qoldiring:\n\n"
        "📌 Matn yozishingiz mumkin\n"
        "📌 Rasm, video yoki video xabar (videonote) yuborishingiz mumkin\n"
        "📌 Ovozli xabar (golos) yuborishingiz mumkin\n\n"
        "Eslatma: Birinchi xabar yuboring, keyin baholash so'rovi chiqadi.",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(FeedbackStates.waiting_feedback_text, F.text)
async def got_text(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if len(text) < 5:
        await message.answer("Iltimos, fikringizni biroz batafsilroq yozib yuboring ✍️")
        return

    await state.update_data(entry_type="text", feedback_text=text, media_type=None, file_id=None)
    await state.set_state(FeedbackStates.waiting_rating)
    await message.answer("Iltimos, xizmatimizni 1 dan 5 gacha baholang:", reply_markup=rating_kb())


@router.message(FeedbackStates.waiting_feedback_text, F.photo)
async def got_photo(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(entry_type="media", media_type="photo", file_id=file_id, feedback_text=None)
    await state.set_state(FeedbackStates.waiting_rating)
    await message.answer("Rahmat! Endi iltimos, 1 dan 5 gacha baholang:", reply_markup=rating_kb())


@router.message(FeedbackStates.waiting_feedback_text, F.video)
async def got_video(message: Message, state: FSMContext):
    file_id = message.video.file_id
    await state.update_data(entry_type="media", media_type="video", file_id=file_id, feedback_text=None)
    await state.set_state(FeedbackStates.waiting_rating)
    await message.answer("Rahmat! Endi iltimos, 1 dan 5 gacha baholang:", reply_markup=rating_kb())


@router.message(FeedbackStates.waiting_feedback_text, F.video_note)
async def got_video_note(message: Message, state: FSMContext):
    file_id = message.video_note.file_id
    await state.update_data(entry_type="media", media_type="video_note", file_id=file_id, feedback_text=None)
    await state.set_state(FeedbackStates.waiting_rating)
    await message.answer("Rahmat! Endi iltimos, 1 dan 5 gacha baholang:", reply_markup=rating_kb())


@router.message(FeedbackStates.waiting_feedback_text, F.voice)
async def got_voice(message: Message, state: FSMContext):
    file_id = message.voice.file_id
    await state.update_data(entry_type="media", media_type="voice", file_id=file_id, feedback_text=None)
    await state.set_state(FeedbackStates.waiting_rating)
    await message.answer("Rahmat! Endi iltimos, 1 dan 5 gacha baholang:", reply_markup=rating_kb())


@router.message(FeedbackStates.waiting_rating)
async def got_rating(message: Message, state: FSMContext):
    t = (message.text or "").strip()
    rating = None

    if t.startswith("⭐"):
        parts = t.split()
        if len(parts) == 2 and parts[1].isdigit():
            rating = int(parts[1])

    if rating is None and t.isdigit():
        rating = int(t)

    if rating not in [1, 2, 3, 4, 5]:
        await message.answer("Iltimos, 1 dan 5 gacha bo'lgan baholardan birini tanlang ⭐")
        return

    await state.update_data(rating=rating)
    await state.set_state(FeedbackStates.waiting_phone)
    await message.answer(
        "Iltimos, agar sizga qulay bo'lsa, telefon raqamingizni qoldiring 📱\nShunda zarur hollarda siz bilan bog'lanishimiz mumkin.\n\n"
        "Eslatma: bu mutlaqo ixtiyoriy 😊",
        reply_markup=phone_kb()
    )


@router.message(FeedbackStates.waiting_phone, F.contact)
async def got_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else None
    await finalize(message, state, phone)


@router.message(FeedbackStates.waiting_phone, F.text == "⏭ O'tkazib yuborish")
async def skip_phone(message: Message, state: FSMContext):
    await finalize(message, state, None)


@router.message(FeedbackStates.waiting_phone)
async def phone_help(message: Message, state: FSMContext):
    await message.answer(
        "Iltimos, telefon raqamini 📞 tugma orqali yuboring yoki ⏭ O'tkazib yuborishni tanlang.",
        reply_markup=phone_kb()
    )


async def finalize(message: Message, state: FSMContext, phone: str | None):
    if ADMIN_CHAT_ID == 0:
        await message.answer("⚠️ Guruh ID (ADMIN_CHAT_ID) sozlanmagan. .env faylda guruh ID ni kiriting.")
        await state.clear()
        return

    data = await state.get_data()
    uid = str(message.from_user.id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    async with _store_lock:
        store = load_store()
        user = normalize_user(store.get(uid))

        user["full_name"] = message.from_user.full_name
        user["username"] = message.from_user.username
        user["last_rating"] = data.get("rating")
        if phone:
            user["phone"] = phone

        if data.get("entry_type") == "text":
            user["comments"].append({"text": data.get("feedback_text"), "date": now})
        else:
            user["media"].append({
                "type": data.get("media_type"),
                "file_id": data.get("file_id"),
                "date": now
            })

        trim_history(user)

        await delete_old_package(message.bot, ADMIN_CHAT_ID, user.get("group_message_ids", []))

        summary = build_text(uid, user)
        new_ids = await send_package(message.bot, ADMIN_CHAT_ID, summary, user.get("media", []))

        user["group_message_ids"] = new_ids
        store[uid] = user
        save_store(store)

    logger.info("Feedback saqlandi: user_id=%s rating=%s", uid, data.get("rating"))

    await message.answer(
        "Rahmat! ✅\n"
        "Fikringiz qabul qilindi.\n\n"
        "Agar yana fikr bildirmoqchi bo'lsangiz, /start buyrug'ini yuboring.",
        reply_markup=ReplyKeyboardRemove()
    )

    await state.clear()
