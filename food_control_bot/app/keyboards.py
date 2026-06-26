from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.filters.callback_data import CallbackData


# ── Callback Data ─────────────────────────────────────────────────────────

class MealSelectCB(CallbackData, prefix="ms"):
    meal: int

class MealChoiceCB(CallbackData, prefix="mc"):
    meal: int
    ch: str

class MealBackCB(CallbackData, prefix="mb"):
    pass

class MealConfirmCB(CallbackData, prefix="mconf"):
    act: str

class ReportMealCB(CallbackData, prefix="rm"):
    meal: int

class AdminPanelCB(CallbackData, prefix="ap"):
    section: str  # "main","status","employees","tomorrow","settings","edit"

class AdminEditOrderCB(CallbackData, prefix="aeo"):
    user_id: int  # telegram_id of employee to edit

class AdminToggleMealCB(CallbackData, prefix="atm"):
    user_id: int
    meal: int     # 1 or 2


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


# ── Meal Selection (13:30 xabari) ─────────────────────────────────────────

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


# ── Meal Report ───────────────────────────────────────────────────────────

def report_meal_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="1-ovqat", callback_data=ReportMealCB(meal=1).pack()),
        InlineKeyboardButton(text="2-ovqat", callback_data=ReportMealCB(meal=2).pack()),
    ]])


# ── Admin Panel ───────────────────────────────────────────────────────────

def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Bugungi holat",       callback_data=AdminPanelCB(section="status").pack()),
            InlineKeyboardButton(text="👥 Xodimlar",            callback_data=AdminPanelCB(section="employees").pack()),
        ],
        [
            InlineKeyboardButton(text="📊 Ertangi buyurtmalar", callback_data=AdminPanelCB(section="tomorrow").pack()),
            InlineKeyboardButton(text="⚙️ Sozlamalar",          callback_data=AdminPanelCB(section="settings").pack()),
        ],
        [
            InlineKeyboardButton(text="✏️ Buyurtmalarni tahrirlash", callback_data=AdminPanelCB(section="edit").pack()),
        ],
    ])


def admin_settings_keyboard(group_id=None) -> InlineKeyboardMarkup:
    btn_label = "✏️ Guruh ID o'zgartirish" if group_id else "📍 Guruh ID sozlash"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_label, callback_data=AdminPanelCB(section="set_group").pack())],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=AdminPanelCB(section="main").pack())],
    ])


def admin_back_keyboard(refresh_section: str = "") -> InlineKeyboardMarkup:
    buttons = []
    if refresh_section:
        buttons.append(InlineKeyboardButton(
            text="🔄 Yangilash",
            callback_data=AdminPanelCB(section=refresh_section).pack()
        ))
    buttons.append(InlineKeyboardButton(
        text="⬅️ Orqaga",
        callback_data=AdminPanelCB(section="main").pack()
    ))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def admin_edit_list_keyboard(users_orders: list) -> InlineKeyboardMarkup:
    """users_orders: list of (user_dict, order_dict_or_None)"""
    rows = []
    pair = []
    for u, o in users_orders:
        if o and o.get("is_confirmed"):
            m1 = "✅" if o["meal_1_status"] == "yes" else "❌"
            m2 = "✅" if o["meal_2_status"] == "yes" else "❌"
            label = f"{_short_name(u)} {m1}{m2}"
        else:
            label = f"{_short_name(u)} ⏳"
        pair.append(InlineKeyboardButton(
            text=label,
            callback_data=AdminEditOrderCB(user_id=u["telegram_id"]).pack()
        ))
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)

    rows.append([
        InlineKeyboardButton(text="🔄 Yangilash", callback_data=AdminPanelCB(section="edit").pack()),
        InlineKeyboardButton(text="⬅️ Orqaga",   callback_data=AdminPanelCB(section="main").pack()),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_edit_user_keyboard(user_id: int, m1_status, m2_status) -> InlineKeyboardMarkup:
    """Toggle buttons for a specific user's order."""
    def toggle_btn(meal: int, status):
        if status == "yes":
            text = f"❌ {meal}-ovqatni yemaydi qilish"
        elif status == "no":
            text = f"✅ {meal}-ovqatni yeydi qilish"
        else:
            text = f"✅ {meal}-ovqat — tasdiqlash"
        return InlineKeyboardButton(
            text=text,
            callback_data=AdminToggleMealCB(user_id=user_id, meal=meal).pack()
        )

    return InlineKeyboardMarkup(inline_keyboard=[
        [toggle_btn(1, m1_status)],
        [toggle_btn(2, m2_status)],
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data=AdminEditOrderCB(user_id=user_id).pack()),
            InlineKeyboardButton(text="⬅️ Ro'yxat",  callback_data=AdminPanelCB(section="edit").pack()),
        ],
    ])


def _short_name(u: dict) -> str:
    if u.get("username"):
        nick = f"@{u['username']}"
        return nick[:15]
    name = u.get("full_name") or f"ID{u['telegram_id']}"
    return name[:15]
