"""Employee reply-keyboard menus."""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def employee_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Mening ish vazifalarim grafigi")],
            [KeyboardButton(text="📋 Topshiriqni tanlash"), KeyboardButton(text="⏰ Deadline yaqinlashganlar")],
            [KeyboardButton(text="🏁 Tugatilganlar"), KeyboardButton(text="🔄 Grafikni yangilash")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Menyudan tanlang",
    )
