"""Admin reply-keyboard menus."""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def admin_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Topshiriq berish"), KeyboardButton(text="📋 Faol topshiriqlar")],
            [KeyboardButton(text="🏁 Tugatilgan topshiriqlar"), KeyboardButton(text="⏰ Deadline yaqinlashganlar")],
            [KeyboardButton(text="⚠️ Kechikkan topshiriqlar"), KeyboardButton(text="📊 Ish vazifalari grafigi")],
            [KeyboardButton(text="👥 Xodimlar"), KeyboardButton(text="⚙️ Sozlamalar")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Admin menyusidan tanlang",
    )
