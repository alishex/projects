import asyncio
import html
import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
VACANCY_CHANNEL_ID_RAW = os.getenv("VACANCY_CHANNEL_ID", "")
RESUME_CHANNEL_ID_RAW = os.getenv("RESUME_CHANNEL_ID", "")
VACANCY_CHANNEL_NICK = os.getenv("VACANCY_CHANNEL_NICK", "@vakansiya_kanali").strip()
RESUME_CHANNEL_NICK = os.getenv("RESUME_CHANNEL_NICK", "@rezume_kanali").strip()
DB_PATH = os.getenv("DB_PATH", "bot_data.db")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

Field = Dict[str, str]


# =========================
# CONFIG
# =========================
def parse_admin_ids(raw: str) -> set[int]:
    result: set[int] = set()
    for item in raw.split(","):
        item = item.strip()
        if item and item.lstrip("-").isdigit():
            result.add(int(item))
    return result


def parse_chat_id(raw: str) -> Union[int, str]:
    value = raw.strip()
    if not value:
        raise ValueError("Kanal ID bo'sh")
    if value.startswith("@"):
        return value
    if value.lstrip("-").isdigit():
        return int(value)
    return value


ADMIN_IDS = parse_admin_ids(ADMIN_IDS_RAW)
VACANCY_CHANNEL_ID = parse_chat_id(VACANCY_CHANNEL_ID_RAW) if VACANCY_CHANNEL_ID_RAW else ""
RESUME_CHANNEL_ID = parse_chat_id(RESUME_CHANNEL_ID_RAW) if RESUME_CHANNEL_ID_RAW else ""


# =========================
# DATABASE
# =========================
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            full_name TEXT,
            form_type TEXT NOT NULL,
            data_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            admin_message_chat_id INTEGER,
            admin_message_id INTEGER,
            channel_message_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def create_submission(
    user_id: int,
    username: Optional[str],
    full_name: str,
    form_type: str,
    data: Dict[str, Any],
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.now().isoformat(timespec="seconds")
    cur.execute(
        """
        INSERT INTO submissions (
            user_id, username, full_name, form_type, data_json, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
        """,
        (user_id, username, full_name, form_type, json.dumps(data, ensure_ascii=False), now, now),
    )
    conn.commit()
    submission_id = int(cur.lastrowid)
    conn.close()
    return submission_id

def update_submission_admin_message(submission_id: int, chat_id: int, message_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE submissions
        SET admin_message_chat_id = ?, admin_message_id = ?, updated_at = ?
        WHERE id = ?
        """,
        (chat_id, message_id, datetime.now().isoformat(timespec="seconds"), submission_id),
    )
    conn.commit()
    conn.close()


def update_submission_status(submission_id: int, status: str, channel_message_id: Optional[int] = None) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE submissions
        SET status = ?, channel_message_id = COALESCE(?, channel_message_id), updated_at = ?
        WHERE id = ?
        """,
        (status, channel_message_id, datetime.now().isoformat(timespec="seconds"), submission_id),
    )
    conn.commit()
    conn.close()


def get_submission(submission_id: int) -> Optional[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,))
    row = cur.fetchone()
    conn.close()
    return row


# =========================
# FORMS (SHORT VERSION)
# =========================
VACANCY_FIELDS: List[Field] = [
    {
        "key": "job_title",
        "label": "Lavozim",
        "icon": "📌",
        "question": "Qanday xodim kerak?",
        "example": "Masalan: Sotuv menejeri",
    },
    {
        "key": "company_name",
        "label": "Kompaniya",
        "icon": "🏢",
        "question": "Kompaniya nomini kiriting.",
        "example": "Masalan: Techno Soft",
    },
    {
        "key": "salary",
        "label": "Oylik",
        "icon": "💰",
        "question": "Oylik yoki maosh oralig'ini yozing.",
        "example": "Masalan: 4 000 000 - 7 000 000 so'm",
    },
    {
        "key": "location",
        "label": "Manzil",
        "icon": "📍",
        "question": "Ish joyi qayerda?",
        "example": "Masalan: Toshkent shahar, Chilonzor",
    },
    {
        "key": "schedule",
        "label": "Ish vaqti",
        "icon": "⏰",
        "question": "Ish kunlari va vaqtini yozing.",
        "example": "Masalan: Dushanba-Shanba, 09:00-18:00",
    },
    {
        "key": "requirements",
        "label": "Talablar",
        "icon": "✅",
        "question": "Nomzod uchun asosiy talablarni qisqacha yozing.",
        "example": "Masalan: xushmuomala, mas'uliyatli, 1 yil tajriba",
    },
    {
        "key": "contact_phone",
        "label": "Telefon",
        "icon": "📞",
        "question": "Aloqa uchun telefon raqamini kiriting.",
        "example": "Masalan: +998 90 123 45 67",
    },
    {
        "key": "telegram_username",
        "label": "Telegram",
        "icon": "💬",
        "question": "Telegram username yoki link yozing.",
        "example": "Masalan: @hr_manager",
    },
]

RESUME_FIELDS: List[Field] = [
    {
        "key": "full_name",
        "label": "F.I.Sh",
        "icon": "👤",
        "question": "To'liq ism-familiyangizni kiriting.",
        "example": "Masalan: Jamshid Qodirov",
    },
    {
        "key": "position",
        "label": "Mutaxassislik",
        "icon": "💼",
        "question": "Qaysi lavozim bo'yicha ish qidirmoqdasiz?",
        "example": "Masalan: Grafik dizayner",
    },
    {
        "key": "experience",
        "label": "Tajriba",
        "icon": "🎯",
        "question": "Ish tajribangizni qisqacha yozing.",
        "example": "Masalan: 2 yil SMM menejer bo'lib ishlaganman",
    },
    {
        "key": "city",
        "label": "Yashash joyi",
        "icon": "📍",
        "question": "Qaysi shahar yoki tumanda yashaysiz?",
        "example": "Masalan: Toshkent, Yunusobod",
    },
    {
        "key": "salary_expectation",
        "label": "Kutilayotgan oylik",
        "icon": "💰",
        "question": "Kutilayotgan oylikni yozing.",
        "example": "Masalan: 6 000 000 so'm",
    },
    {
        "key": "skills",
        "label": "Ko'nikmalar",
        "icon": "🧠",
        "question": "Asosiy ko'nikmalaringizni yozing.",
        "example": "Masalan: Photoshop, Canva, SMM, Copywriting",
    },
    {
        "key": "phone",
        "label": "Telefon",
        "icon": "📞",
        "question": "Telefon raqamingizni kiriting.",
        "example": "Masalan: +998 90 123 45 67",
    },
    {
        "key": "telegram_username",
        "label": "Telegram",
        "icon": "💬",
        "question": "Telegram username yoki link yozing.",
        "example": "Masalan: @jamshid_work",
    },
]

FORM_MAP: Dict[str, Dict[str, Any]] = {
    "vacancy": {
        "title": "Vakansiya",
        "emoji": "💼",
        "intro": (
            "<b>Vakansiya joylash</b>\n"
            "Qisqa forma orqali e'lon yuborasiz.\n"
            "Faqat eng kerakli ma'lumotlar olinadi."
        ),
        "fields": VACANCY_FIELDS,
    },
    "resume": {
        "title": "Rezyume",
        "emoji": "📄",
        "intro": (
            "<b>Rezyume joylash</b>\n"
            "Qisqa forma orqali o'zingiz haqingizda asosiy ma'lumotlarni yuborasiz.\n"
            "Faqat eng kerakli maydonlar so'raladi."
        ),
        "fields": RESUME_FIELDS,
    },
}


# =========================
# FSM
# =========================
class FormFlow(StatesGroup):
    filling = State()
    reviewing = State()


# =========================
# KEYBOARDS
# =========================
def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💼 Vakansiya joylash", callback_data="sf:vacancy")
    builder.button(text="📄 Rezyume joylash", callback_data="sf:resume")
    builder.adjust(1)
    return builder.as_markup()


def preview_kb(form_type: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Yuborish", callback_data=f"submit:{form_type}")
    builder.button(text="✏️ Tahrirlash", callback_data=f"editm:{form_type}")
    builder.button(text="❌ Bekor qilish", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def edit_fields_kb(form_type: str, fields: List[Field]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i, _field in enumerate(fields, start=1):
        builder.button(text=str(i), callback_data=f"editf:{form_type}:{i - 1}")
    builder.button(text="🔙 Preview ga qaytish", callback_data=f"backp:{form_type}")
    builder.adjust(4)
    return builder.as_markup()


def admin_review_kb(submission_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data=f"approve:{submission_id}")
    builder.button(text="❌ Rad etish", callback_data=f"reject:{submission_id}")
    builder.adjust(2)
    return builder.as_markup()


def home_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Bosh menyu", callback_data="home")
    return builder.as_markup()


# =========================
# HELPERS
# =========================
def normalize_text(value: str) -> str:
    return value.strip()


def esc(value: Any) -> str:
    return html.escape(str(value))


def get_fields(form_type: str) -> List[Field]:
    return FORM_MAP[form_type]["fields"]


def field_value(data: Dict[str, Any], key: str, default: str = "—") -> str:
    value = str(data.get(key, default)).strip()
    return value if value else default


def make_user_link(username: Optional[str], full_name: str, user_id: int) -> str:
    if username:
        return f"@{esc(username)}"
    return f'<a href="tg://user?id={user_id}">{esc(full_name)}</a>'


def get_channel_info(form_type: str) -> Dict[str, Union[int, str]]:
    if form_type == "vacancy":
        return {
            "channel_id": VACANCY_CHANNEL_ID,
            "channel_nick": VACANCY_CHANNEL_NICK or str(VACANCY_CHANNEL_ID),
            "footer_title": "Ko'proq vakansiyalar",
        }
    return {
        "channel_id": RESUME_CHANNEL_ID,
        "channel_nick": RESUME_CHANNEL_NICK or str(RESUME_CHANNEL_ID),
        "footer_title": "Ko'proq rezyumelar",
    }


def build_channel_footer(form_type: str) -> str:
    info = get_channel_info(form_type)
    return (
        "\n\n━━━━━━━━━━━━━━\n"
        f"📢 <b>{esc(info['footer_title'])}:</b> {esc(info['channel_nick'])}\n"
        "🚀 <i>Kanalga obuna bo'ling</i>"
    )


def build_question_text(form_type: str, step: int) -> str:
    fields = get_fields(form_type)
    field = fields[step]
    total = len(fields)
    title = FORM_MAP[form_type]["title"]
    emoji = FORM_MAP[form_type]["emoji"]
    return (
        f"{emoji} <b>{esc(title)} formasi</b>\n"
        f"<b>Qadam:</b> {step + 1}/{total}\n\n"
        f"{field['icon']} <b>{esc(field['label'])}</b>\n"
        f"{esc(field['question'])}\n\n"
        f"<i>{esc(field['example'])}</i>"
    )


def build_preview_text(form_type: str, data: Dict[str, Any]) -> str:
    meta = FORM_MAP[form_type]
    lines = [
        f"{meta['emoji']} <b>{esc(meta['title'])} preview</b>",
        "",
        "Ma'lumotlarni tekshirib chiqing.",
        "To'g'ri bo'lsa yuboring, xato bo'lsa tahrirlang.",
        "",
    ]
    for i, field in enumerate(meta["fields"], start=1):
        lines.append(f"{field['icon']} <b>{i}. {esc(field['label'])}</b>: {esc(field_value(data, field['key']))}")
    return "\n".join(lines)


def build_vacancy_post(data: Dict[str, Any]) -> str:
    return (
        "💼 <b>VAKANSIYA</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"📌 <b>Lavozim:</b> {esc(field_value(data, 'job_title'))}\n"
        f"🏢 <b>Kompaniya:</b> {esc(field_value(data, 'company_name'))}\n"
        f"💰 <b>Oylik:</b> {esc(field_value(data, 'salary'))}\n"
        f"📍 <b>Manzil:</b> {esc(field_value(data, 'location'))}\n"
        f"⏰ <b>Ish vaqti:</b> {esc(field_value(data, 'schedule'))}\n"
        f"✅ <b>Talablar:</b> {esc(field_value(data, 'requirements'))}\n"
        f"📞 <b>Telefon:</b> {esc(field_value(data, 'contact_phone'))}\n"
        f"💬 <b>Telegram:</b> {esc(field_value(data, 'telegram_username'))}"
    )


def build_resume_post(data: Dict[str, Any]) -> str:
    return (
        "📄 <b>REZYUME</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"👤 <b>F.I.Sh:</b> {esc(field_value(data, 'full_name'))}\n"
        f"💼 <b>Mutaxassislik:</b> {esc(field_value(data, 'position'))}\n"
        f"🎯 <b>Tajriba:</b> {esc(field_value(data, 'experience'))}\n"
        f"📍 <b>Yashash joyi:</b> {esc(field_value(data, 'city'))}\n"
        f"💰 <b>Kutilayotgan oylik:</b> {esc(field_value(data, 'salary_expectation'))}\n"
        f"🧠 <b>Ko'nikmalar:</b> {esc(field_value(data, 'skills'))}\n"
        f"📞 <b>Telefon:</b> {esc(field_value(data, 'phone'))}\n"
        f"💬 <b>Telegram:</b> {esc(field_value(data, 'telegram_username'))}"
    )


def build_publish_text(form_type: str, data: Dict[str, Any]) -> str:
    if form_type == "vacancy":
        return build_vacancy_post(data) + build_channel_footer(form_type)
    return build_resume_post(data) + build_channel_footer(form_type)


def build_admin_text(submission_id: int, form_type: str, data: Dict[str, Any], user: Any) -> str:
    title = FORM_MAP[form_type]["title"]
    username = make_user_link(user.username, user.full_name, user.id)
    channel_info = get_channel_info(form_type)
    return (
        "🛎 <b>Yangi e'lon tasdiq uchun keldi</b>\n"
        f"🆔 <b>ID:</b> {submission_id}\n"
        f"📂 <b>Tur:</b> {esc(title)}\n"
        f"👤 <b>Foydalanuvchi:</b> {esc(user.full_name)}\n"
        f"🔗 <b>Username:</b> {username}\n"
        f"📣 <b>Joylanadigan kanal:</b> {esc(channel_info['channel_nick'])}\n\n"
        f"{build_publish_text(form_type, data)}"
    )


def build_success_submit_text(form_type: str) -> str:
    info = get_channel_info(form_type)
    return (
        "✅ <b>Qabul qilindi</b>\n\n"
        "E'loningiz adminga yuborildi.\n"
        f"Tasdiqlansa, <b>{esc(info['channel_nick'])}</b> kanaliga joylanadi."
    )


def build_reject_user_text() -> str:
    return (
        "❌ <b>E'lon rad etildi</b>\n\n"
        "Admin e'lonni tasdiqlamadi.\n"
        "Kerak bo'lsa qaytadan to'ldirib yuborishingiz mumkin."
    )


def build_approved_user_text(form_type: str) -> str:
    info = get_channel_info(form_type)
    return (
        "🎉 <b>Tabriklaymiz</b>\n\n"
        f"Sizning e'loningiz tasdiqlandi va <b>{esc(info['channel_nick'])}</b> kanaliga joylandi."
    )


def build_edit_menu_text(form_type: str) -> str:
    fields = get_fields(form_type)
    lines = ["✏️ <b>Tahrirlash bo'limi</b>", "Qaysi bandni o'zgartirmoqchisiz?", ""]
    for i, field in enumerate(fields, start=1):
        lines.append(f"{field['icon']} <b>{i}.</b> {esc(field['label'])}")
    return "\n".join(lines)


async def ask_current_question(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await message.answer(build_question_text(data["form_type"], int(data["step"])), reply_markup=home_kb())


async def show_preview(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await message.answer(build_preview_text(data["form_type"], data.get("values", {})), reply_markup=preview_kb(data["form_type"]))


# =========================
# BOT LOGIC
# =========================
class _AdminCheck:
    @staticmethod
    async def is_admin(user_id: int) -> bool:
        return user_id in ADMIN_IDS


async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = (
        "Assalomu alaykum 👋\n\n"
        "Bu bot orqali siz qisqa forma bilan:\n"
        "• vakansiya joylashingiz\n"
        "• rezyume qoldirishingiz mumkin\n\n"
        "Kerakli bo'limni tanlang:"
    )
    await message.answer(text, reply_markup=main_menu_kb())


async def start_form(callback: CallbackQuery, state: FSMContext) -> None:
    form_type = callback.data.split(":", 1)[1]
    await state.clear()
    await state.update_data(form_type=form_type, step=0, values={}, edit_mode=False)
    await state.set_state(FormFlow.filling)

    meta = FORM_MAP[form_type]
    channel_info = get_channel_info(form_type)
    await callback.message.answer(
        f"{meta['emoji']} {meta['intro']}\n\n📣 <b>Joylanadigan kanal:</b> {esc(channel_info['channel_nick'])}"
    )
    await ask_current_question(callback.message, state)
    await callback.answer()


async def collect_answer(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Iltimos, javobni matn ko'rinishida yuboring.")
        return

    data = await state.get_data()
    form_type = data["form_type"]
    step = int(data["step"])
    edit_mode = bool(data.get("edit_mode", False))
    values = dict(data.get("values", {}))

    field = get_fields(form_type)[step]
    values[field["key"]] = normalize_text(message.text)
    await state.update_data(values=values)

    if edit_mode:
        await state.update_data(edit_mode=False)
        await state.set_state(FormFlow.reviewing)
        await message.answer("✅ Tahrir saqlandi.")
        await show_preview(message, state)
        return

    next_step = step + 1
    if next_step >= len(get_fields(form_type)):
        await state.set_state(FormFlow.reviewing)
        await message.answer("📋 <b>Forma tayyor</b>\nMa'lumotlarni tekshirib chiqing.")
        await show_preview(message, state)
        return

    await state.update_data(step=next_step)
    await ask_current_question(message, state)


async def open_edit_menu(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    form_type = data["form_type"]
    await callback.message.answer(
        build_edit_menu_text(form_type),
        reply_markup=edit_fields_kb(form_type, get_fields(form_type)),
    )
    await callback.answer()


async def select_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    _, form_type, index_raw = callback.data.split(":")
    index = int(index_raw)
    field = get_fields(form_type)[index]
    await state.update_data(step=index, edit_mode=True)
    await state.set_state(FormFlow.filling)
    await callback.message.answer(
        f"✏️ <b>Tahrirlash</b>\n\n{field['icon']} <b>{esc(field['label'])}</b>\n"
        f"{esc(field['question'])}\n\n<i>{esc(field['example'])}</i>",
        reply_markup=home_kb(),
    )
    await callback.answer()


async def back_preview(callback: CallbackQuery, state: FSMContext) -> None:
    await show_preview(callback.message, state)
    await callback.answer()


async def submit_form(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if not ADMIN_IDS:
        await callback.message.answer("ADMIN_IDS noto'g'ri kiritilgan.")
        await callback.answer()
        return

    data = await state.get_data()
    form_type = data["form_type"]
    values = data.get("values", {})
    channel_info = get_channel_info(form_type)

    if not channel_info["channel_id"]:
        await callback.message.answer("Kanal sozlamasi to'ldirilmagan.")
        await callback.answer()
        return

    user = callback.from_user
    submission_id = create_submission(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        form_type=form_type,
        data=values,
    )

    admin_text = build_admin_text(submission_id, form_type, values, user)
    first_admin_message: Optional[Message] = None
    success_count = 0

    for admin_id in ADMIN_IDS:
        try:
            sent = await bot.send_message(admin_id, admin_text, reply_markup=admin_review_kb(submission_id))
            success_count += 1
            if first_admin_message is None:
                first_admin_message = sent
        except Exception as exc:
            logger.exception("Admin ga yuborishda xato: %s", exc)

    if success_count == 0:
        await callback.message.answer(
            "Adminlarga yuborib bo'lmadi. Avval adminlar botga /start bosgan bo'lishi kerak."
        )
        await callback.answer()
        return

    if first_admin_message is not None:
        update_submission_admin_message(submission_id, first_admin_message.chat.id, first_admin_message.message_id)

    await callback.message.answer(build_success_submit_text(form_type), reply_markup=home_kb())
    await state.clear()
    await callback.answer("Yuborildi")


async def admin_approve(callback: CallbackQuery, bot: Bot) -> None:
    if not await _AdminCheck.is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz", show_alert=True)
        return

    submission_id = int(callback.data.split(":", 1)[1])
    row = get_submission(submission_id)
    if not row:
        await callback.answer("Topilmadi", show_alert=True)
        return
    if row["status"] == "approved":
        await callback.answer("Allaqachon tasdiqlangan", show_alert=True)
        return
    if row["status"] == "rejected":
        await callback.answer("Allaqachon rad etilgan", show_alert=True)
        return

    form_type = str(row["form_type"])
    data = json.loads(str(row["data_json"]))
    channel_info = get_channel_info(form_type)
    text = build_publish_text(form_type, data)

    try:
        sent = await bot.send_message(channel_info["channel_id"], text)
    except Exception as exc:
        logger.exception("Kanalga yuborishda xato: %s", exc)
        await callback.answer("Kanalga yuborib bo'lmadi", show_alert=True)
        return

    update_submission_status(submission_id, "approved", sent.message_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("✅ Tasdiqlandi va kanalga yuborildi.")

    try:
        await bot.send_message(int(row["user_id"]), build_approved_user_text(form_type), reply_markup=main_menu_kb())
    except Exception as exc:
        logger.exception("User ga approve xabari yuborishda xato: %s", exc)

    await callback.answer("Tasdiqlandi")


async def admin_reject(callback: CallbackQuery, bot: Bot) -> None:
    if not await _AdminCheck.is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz", show_alert=True)
        return

    submission_id = int(callback.data.split(":", 1)[1])
    row = get_submission(submission_id)
    if not row:
        await callback.answer("Topilmadi", show_alert=True)
        return
    if row["status"] == "approved":
        await callback.answer("Allaqachon tasdiqlangan", show_alert=True)
        return
    if row["status"] == "rejected":
        await callback.answer("Allaqachon rad etilgan", show_alert=True)
        return

    update_submission_status(submission_id, "rejected")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("❌ E'lon rad etildi.")

    try:
        await bot.send_message(int(row["user_id"]), build_reject_user_text(), reply_markup=main_menu_kb())
    except Exception as exc:
        logger.exception("User ga reject xabari yuborishda xato: %s", exc)

    await callback.answer("Rad etildi")


async def cancel_form(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("❌ Jarayon bekor qilindi.", reply_markup=main_menu_kb())
    await callback.answer()


async def go_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("🏠 Bosh menyu", reply_markup=main_menu_kb())
    await callback.answer()


async def fallback_text(message: Message) -> None:
    await message.answer("Jarayonni boshlash uchun /start bosing.")


# =========================
# MAIN
# =========================
async def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN kiritilmagan. .env faylni to'ldiring.")
    if not ADMIN_IDS:
        raise ValueError("ADMIN_IDS kiritilmagan yoki noto'g'ri.")
    if not VACANCY_CHANNEL_ID:
        raise ValueError("VACANCY_CHANNEL_ID kiritilmagan yoki noto'g'ri.")
    if not RESUME_CHANNEL_ID:
        raise ValueError("RESUME_CHANNEL_ID kiritilmagan yoki noto'g'ri.")

    init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.register(cmd_start, CommandStart())

    dp.callback_query.register(start_form, F.data.startswith("sf:"))
    dp.callback_query.register(open_edit_menu, F.data.startswith("editm:"), FormFlow.reviewing)
    dp.callback_query.register(select_edit_field, F.data.startswith("editf:"), FormFlow.reviewing)
    dp.callback_query.register(back_preview, F.data.startswith("backp:"), FormFlow.reviewing)
    dp.callback_query.register(submit_form, F.data.startswith("submit:"), FormFlow.reviewing)

    dp.callback_query.register(admin_approve, F.data.startswith("approve:"))
    dp.callback_query.register(admin_reject, F.data.startswith("reject:"))

    dp.callback_query.register(cancel_form, F.data == "cancel")
    dp.callback_query.register(go_home, F.data == "home")

    dp.message.register(collect_answer, FormFlow.filling, F.text)
    dp.message.register(fallback_text)

    logger.info("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
