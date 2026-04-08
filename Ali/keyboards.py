from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup

EXPENSE_CATEGORIES = [
    ['Ovqat', 'Transport'],
    ['Uy', 'Sog\'liq'],
    ['Kiyim', 'O\'qish'],
    ['Sovg\'a', 'Boshqa'],
]

INCOME_CATEGORIES = [
    ['Oylik', 'Savdo'],
    ['Qarz qaytdi', 'Bonus'],
    ['Sovg\'a', 'Boshqa'],
]

ACCOUNT_TYPES = [['💵 Naqd', '💳 Karta']]
CURRENCIES = [['🇺🇿 So\'m', '🇺🇸 Dollar', '🇪🇺 Yevro']]


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton('➕ Kirim qo\'shish'), KeyboardButton('➖ Chiqim qo\'shish')],
        [KeyboardButton('💰 Balans'), KeyboardButton('📊 Bugungi hisobot')],
        [KeyboardButton('🗓 Oylik hisobot'), KeyboardButton('📋 Oxirgi yozuvlar')],
        [KeyboardButton('🗑 Yozuvni o\'chirish'), KeyboardButton('⬇️ CSV yuklab olish')],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)



def category_keyboard(tx_type: str) -> ReplyKeyboardMarkup:
    rows = INCOME_CATEGORIES if tx_type == 'income' else EXPENSE_CATEGORIES
    keyboard = [row[:] for row in rows]
    keyboard.append(['⬅️ Bekor qilish'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)



def account_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [row[:] for row in ACCOUNT_TYPES]
    keyboard.append(['⬅️ Bekor qilish'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)



def currency_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [row[:] for row in CURRENCIES]
    keyboard.append(['⬅️ Bekor qilish'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)



def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([['⬅️ Bekor qilish']], resize_keyboard=True, one_time_keyboard=True)
