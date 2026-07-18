from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.filters.callback_data import CallbackData

BTN_FINAL_REPORT = "🍽 Yakuniy hisobot"
BTN_FEEDBACK = "💬 Fikr-mulohaza"


class StartOrderCb(CallbackData, prefix="start"):
    date: str
    dept_key: str


class MealStepCb(CallbackData, prefix="meal"):
    action: str   # "confirm" | "edit"
    date: str


class EditPickCb(CallbackData, prefix="editpick"):
    dept_key: str


class ReportPickCb(CallbackData, prefix="reportpick"):
    dept_key: str


class FeedbackPickCb(CallbackData, prefix="feedbackpick"):
    dept_key: str


class DelegateCb(CallbackData, prefix="delegate"):
    date: str
    dept_key: str


def poll_keyboard(target_date: str, dept_key: str, show_delegate: bool = False) -> InlineKeyboardMarkup:
    rows = [[
        InlineKeyboardButton(
            text="📝 Buyurtma berish",
            callback_data=StartOrderCb(date=target_date, dept_key=dept_key).pack()
        )
    ]]
    if show_delegate:
        rows.append([
            InlineKeyboardButton(
                text="📨 O'rinbosarga yuborish",
                callback_data=DelegateCb(date=target_date, dept_key=dept_key).pack()
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _dept_pick_keyboard(depts: list, cb_cls) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{d['emoji']} {d['name']}",
            callback_data=cb_cls(dept_key=d["key"]).pack()
        )]
        for d in depts
    ])


def edit_pick_keyboard(depts: list) -> InlineKeyboardMarkup:
    return _dept_pick_keyboard(depts, EditPickCb)


def report_pick_keyboard(depts: list) -> InlineKeyboardMarkup:
    return _dept_pick_keyboard(depts, ReportPickCb)


def feedback_pick_keyboard(depts: list) -> InlineKeyboardMarkup:
    return _dept_pick_keyboard(depts, FeedbackPickCb)


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


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Doimiy pastki menyu — istalgan vaqt bosiladi, kunlik buyurtma
    oqimiga bog'liq emas (/start orqali faollashadi va chatda saqlanib qoladi)."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_FINAL_REPORT), KeyboardButton(text=BTN_FEEDBACK)]],
        resize_keyboard=True,
    )
