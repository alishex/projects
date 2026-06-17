from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def rating_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⭐ 1"), KeyboardButton(text="⭐ 2"), KeyboardButton(text="⭐ 3")],
            [KeyboardButton(text="⭐ 4"), KeyboardButton(text="⭐ 5")]
        ],
        resize_keyboard=True
    )

def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="\U0001f4de Telefon raqamini yuborish", request_contact=True)],
            [KeyboardButton(text="⏭ O'tkazib yuborish")]
        ],
        resize_keyboard=True
    )
