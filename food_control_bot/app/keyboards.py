from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.filters.callback_data import CallbackData


# ── Callback Data ─────────────────────────────────────────────────────────

class MealSelectCB(CallbackData, prefix="ms"):
    meal: int   # 1 or 2

class MealChoiceCB(CallbackData, prefix="mc"):
    meal: int   # 1 or 2
    ch: str     # "yes" or "no"

class MealBackCB(CallbackData, prefix="mb"):
    pass

class MealConfirmCB(CallbackData, prefix="mconf"):
    act: str    # "ok" or "edit"

class ReportMealCB(CallbackData, prefix="rm"):
    meal: int   # 1 or 2


# ── Reply Keyboard ────────────────────────────────────────────────────────

def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🍽 Ovqat hisoboti")]],
        resize_keyboard=True,
        persistent=True,
    )


def remove_keyboard():
    from aiogram.types import ReplyKeyboardRemove
    return ReplyKeyboardRemove()


# ── Meal Selection (17:30 xabari) ─────────────────────────────────────────

def meal_selection_keyboard(m1_status=None, m2_status=None) -> InlineKeyboardMarkup:
    def label(n, status):
        icon = {"yes": "✅ ", "no": "❌ "}.get(status, "")
        return f"{icon}{n}-ovqat"

    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=label(1, m1_status), callback_data=MealSelectCB(meal=1).pack()),
        InlineKeyboardButton(text=label(2, m2_status), callback_data=MealSelectCB(meal=2).pack()),
    ]])


def meal_choice_keyboard(meal: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yeyman",   callback_data=MealChoiceCB(meal=meal, ch="yes").pack()),
            InlineKeyboardButton(text="❌ Yemayman", callback_data=MealChoiceCB(meal=meal, ch="no").pack()),
        ],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=MealBackCB().pack())],
    ])


def meal_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=MealConfirmCB(act="ok").pack()),
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=MealConfirmCB(act="edit").pack()),
    ]])


# ── Meal Report (Ovqat hisoboti button bosqichi) ──────────────────────────

def report_meal_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="1-ovqat", callback_data=ReportMealCB(meal=1).pack()),
        InlineKeyboardButton(text="2-ovqat", callback_data=ReportMealCB(meal=2).pack()),
    ]])
