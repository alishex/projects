from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from app.categories import EXPENSE_CATEGORIES, INCOME_CATEGORIES


def main_menu() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.button(text="➕ Харажат")
    b.button(text="📥 Даромад")
    b.button(text="💼 Маош тушди")
    b.button(text="🤝 Қарз")
    b.button(text="📊 Дашборд")
    b.button(text="📋 Рўйхат")
    b.button(text="📑 Ҳисобот")
    b.button(text="⚙️ Созлаш")
    b.adjust(2, 2, 2, 2)
    return b.as_markup(resize_keyboard=True)


def method_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💵 Нақд", callback_data="method:cash")
    b.button(text="💳 Карта", callback_data="method:card")
    b.adjust(2)
    return b.as_markup()


def category_kb(kind: str) -> InlineKeyboardMarkup:
    cats = EXPENSE_CATEGORIES if kind == "expense" else INCOME_CATEGORIES
    b = InlineKeyboardBuilder()
    for code, label in cats:
        b.button(text=label, callback_data=f"cat:{code}")
    b.adjust(2)
    return b.as_markup()


def period_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Кунлик", callback_data="period:day")
    b.button(text="Ҳафталик", callback_data="period:week")
    b.button(text="Ойлик", callback_data="period:month")
    b.adjust(3)
    return b.as_markup()


def debt_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💸 Бердим", callback_data="debt:given")
    b.button(text="🤲 Олдим", callback_data="debt:taken")
    b.button(text="📋 Очиқ қарзлар", callback_data="debt:list")
    b.adjust(2, 1)
    return b.as_markup()


def settings_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💱 Курс", callback_data="set:rate")
    b.button(text="📊 Ойлик лимит", callback_data="set:monthly_limit")
    b.button(text="📂 Категория лимити", callback_data="set:cat_limit")
    b.button(text="🎙 Овоз ON/OFF", callback_data="set:voice_toggle")
    b.adjust(1)
    return b.as_markup()
