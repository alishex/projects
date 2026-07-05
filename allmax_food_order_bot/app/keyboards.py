from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData


class StartOrderCb(CallbackData, prefix="start"):
    date: str


class MealStepCb(CallbackData, prefix="meal"):
    action: str   # "confirm" | "edit"
    date: str


def poll_keyboard(target_date: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📝 Buyurtma berish",
            callback_data=StartOrderCb(date=target_date).pack()
        )
    ]])


def confirm_keyboard(target_date: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Tasdiqlash",
            callback_data=MealStepCb(action="confirm", date=target_date).pack()
        ),
        InlineKeyboardButton(
            text="✏️ Tahrirlash",
            callback_data=MealStepCb(action="edit", date=target_date).pack()
        ),
    ]])
