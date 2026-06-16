from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📝 Fikr qoldirish")]],
        resize_keyboard=True
    )
