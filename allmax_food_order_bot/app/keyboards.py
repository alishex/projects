from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData


class StartOrderCb(CallbackData, prefix="start"):
    date: str
    dept_key: str


class MealStepCb(CallbackData, prefix="meal"):
    action: str   # "confirm" | "edit"
    date: str


class EditPickCb(CallbackData, prefix="editpick"):
    dept_key: str


def poll_keyboard(target_date: str, dept_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📝 Buyurtma berish",
            callback_data=StartOrderCb(date=target_date, dept_key=dept_key).pack()
        )
    ]])


def edit_pick_keyboard(depts: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{d['emoji']} {d['name']}",
            callback_data=EditPickCb(dept_key=d["key"]).pack()
        )]
        for d in depts
    ])


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
