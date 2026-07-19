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


# ══════════════════════════════════════════════════════════════════════════
# Owner Panel — dasturchisiz boshqarish (bo'limlar/ownerlar/vaqt/menyu/sikl)
# va adminlarni kuzatish/o'rniga buyurtma kiritish.
# ══════════════════════════════════════════════════════════════════════════

class OwnerPanelCB(CallbackData, prefix="op"):
    section: str  # main, status, depts, owners, schedule, menu_edit, cycle, override_pick, report_now


class OwnerDeptDetailCB(CallbackData, prefix="odd"):
    dept_key: str


class OwnerDeptAdminEditCB(CallbackData, prefix="odae"):
    dept_key: str


class OwnerDeptDeputyEditCB(CallbackData, prefix="odde"):
    dept_key: str


class OwnerDeptDeputyRemoveCB(CallbackData, prefix="oddr"):
    dept_key: str


class OwnerDeptFixedToggleCB(CallbackData, prefix="odft"):
    dept_key: str
    to_fixed: int  # 1 = doimiy songa o'tkazish, 0 = admin-so'raladigan turkumga qaytarish


class OwnerDeptFixedEditCB(CallbackData, prefix="odfe"):
    dept_key: str
    meal: int  # 1 yoki 2


class OwnerDeptDeleteCB(CallbackData, prefix="oddel"):
    dept_key: str


class OwnerDeptAddCB(CallbackData, prefix="oda"):
    pass


class OwnerAddCB(CallbackData, prefix="oa"):
    pass


class OwnerRemoveCB(CallbackData, prefix="or"):
    telegram_id: int


class OwnerScheduleEditCB(CallbackData, prefix="ose"):
    field: str  # "poll" yoki "report"


class OwnerOverridePickCB(CallbackData, prefix="oop"):
    dept_key: str


class OwnerMenuWeekCB(CallbackData, prefix="omw"):
    week: int


class OwnerMenuDayCB(CallbackData, prefix="omd"):
    week: int
    day: str


class OwnerMenuEditStartCB(CallbackData, prefix="omes"):
    week: int
    day: str


class OwnerCycleSetCB(CallbackData, prefix="ocs"):
    week: int
    day: str


DAY_NAMES = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
DAY_SHORT = {"Dushanba": "Dush", "Seshanba": "Sesh", "Chorshanba": "Chor", "Payshanba": "Pay",
             "Juma": "Juma", "Shanba": "Shan", "Yakshanba": "Yak"}


def owner_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Ertangi holat", callback_data=OwnerPanelCB(section="status").pack()),
            InlineKeyboardButton(text="✏️ Buyurtma kiritish", callback_data=OwnerPanelCB(section="override_pick").pack()),
        ],
        [
            InlineKeyboardButton(text="🏢 Bo'limlar", callback_data=OwnerPanelCB(section="depts").pack()),
            InlineKeyboardButton(text="👑 Ownerlar", callback_data=OwnerPanelCB(section="owners").pack()),
        ],
        [
            InlineKeyboardButton(text="📝 Menyu", callback_data=OwnerPanelCB(section="menu_edit").pack()),
            InlineKeyboardButton(text="🔄 Sikl", callback_data=OwnerPanelCB(section="cycle").pack()),
        ],
        [
            InlineKeyboardButton(text="🕐 Vaqtlar", callback_data=OwnerPanelCB(section="schedule").pack()),
            InlineKeyboardButton(text="📋 Hisobotni hozir olish", callback_data=OwnerPanelCB(section="report_now").pack()),
        ],
    ])


def owner_back_keyboard(refresh_section: str = "") -> InlineKeyboardMarkup:
    buttons = []
    if refresh_section:
        buttons.append(InlineKeyboardButton(
            text="🔄 Yangilash", callback_data=OwnerPanelCB(section=refresh_section).pack()
        ))
    buttons.append(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=OwnerPanelCB(section="main").pack()))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def owner_status_keyboard(pending_depts: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"✏️ {d['emoji']} {d['name']} uchun kiritish",
            callback_data=OwnerOverridePickCB(dept_key=d["key"]).pack()
        )]
        for d in pending_depts
    ]
    rows.append([
        InlineKeyboardButton(text="🔄 Yangilash", callback_data=OwnerPanelCB(section="status").pack()),
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data=OwnerPanelCB(section="main").pack()),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def owner_override_pick_keyboard(depts: list) -> InlineKeyboardMarkup:
    """depts — doimiy son BO'LMAGAN bo'limlar (owner istalgan birini tanlab,
    o'rniga kirita oladi, javob bergan-bermaganidan qat'i nazar)."""
    rows = [
        [InlineKeyboardButton(text=f"{d['emoji']} {d['name']}", callback_data=OwnerOverridePickCB(dept_key=d["key"]).pack())]
        for d in depts
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=OwnerPanelCB(section="main").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def owner_depts_keyboard(depts: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{d['emoji']} {d['name']}", callback_data=OwnerDeptDetailCB(dept_key=d["key"]).pack())]
        for d in depts
    ]
    rows.append([InlineKeyboardButton(text="➕ Yangi bo'lim qo'shish", callback_data=OwnerDeptAddCB().pack())])
    rows.append([
        InlineKeyboardButton(text="🔄 Yangilash", callback_data=OwnerPanelCB(section="depts").pack()),
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data=OwnerPanelCB(section="main").pack()),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def owner_dept_detail_keyboard(dept: dict) -> InlineKeyboardMarkup:
    is_fixed = dept.get("fixed_meal1") is not None
    rows = []
    if is_fixed:
        rows.append([InlineKeyboardButton(
            text="✏️ Tushlik sonini o'zgartirish",
            callback_data=OwnerDeptFixedEditCB(dept_key=dept["key"], meal=1).pack()
        )])
        rows.append([InlineKeyboardButton(
            text="✏️ Kechki sonini o'zgartirish",
            callback_data=OwnerDeptFixedEditCB(dept_key=dept["key"], meal=2).pack()
        )])
        rows.append([InlineKeyboardButton(
            text="🔓 Doimiy sondan chiqarish (admin tayinlanadi)",
            callback_data=OwnerDeptFixedToggleCB(dept_key=dept["key"], to_fixed=0).pack()
        )])
    else:
        rows.append([InlineKeyboardButton(
            text="✏️ Adminni o'zgartirish",
            callback_data=OwnerDeptAdminEditCB(dept_key=dept["key"]).pack()
        )])
        if dept.get("deputy_id"):
            rows.append([InlineKeyboardButton(
                text="✏️ O'rinbosarni o'zgartirish",
                callback_data=OwnerDeptDeputyEditCB(dept_key=dept["key"]).pack()
            )])
            rows.append([InlineKeyboardButton(
                text="🗑 O'rinbosarni olib tashlash",
                callback_data=OwnerDeptDeputyRemoveCB(dept_key=dept["key"]).pack()
            )])
        else:
            rows.append([InlineKeyboardButton(
                text="➕ O'rinbosar belgilash",
                callback_data=OwnerDeptDeputyEditCB(dept_key=dept["key"]).pack()
            )])
        rows.append([InlineKeyboardButton(
            text="🔒 Doimiy son qilib belgilash",
            callback_data=OwnerDeptFixedToggleCB(dept_key=dept["key"], to_fixed=1).pack()
        )])
    rows.append([InlineKeyboardButton(text="🗑 Bo'limni o'chirish", callback_data=OwnerDeptDeleteCB(dept_key=dept["key"]).pack())])
    rows.append([
        InlineKeyboardButton(text="🔄 Yangilash", callback_data=OwnerDeptDetailCB(dept_key=dept["key"]).pack()),
        InlineKeyboardButton(text="⬅️ Ro'yxat", callback_data=OwnerPanelCB(section="depts").pack()),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def owner_owners_keyboard(owners: list) -> InlineKeyboardMarkup:
    rows = []
    for o in owners:
        label = o.get("full_name") or str(o["telegram_id"])
        if len(owners) <= 1:
            # Kamida bitta owner qolishi shart — yagona ownerni o'chirish
            # tugmasi ko'rsatilmaydi (botdan hech kim boshqarilmasdan qolib
            # ketmasligi uchun).
            rows.append([InlineKeyboardButton(text=f"👑 {label} (yagona owner)", callback_data=OwnerPanelCB(section="owners").pack())])
        else:
            rows.append([InlineKeyboardButton(text=f"❌ {label}", callback_data=OwnerRemoveCB(telegram_id=o["telegram_id"]).pack())])
    rows.append([InlineKeyboardButton(text="➕ Owner qo'shish", callback_data=OwnerAddCB().pack())])
    rows.append([
        InlineKeyboardButton(text="🔄 Yangilash", callback_data=OwnerPanelCB(section="owners").pack()),
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data=OwnerPanelCB(section="main").pack()),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def owner_schedule_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ So'rov yuborish vaqti", callback_data=OwnerScheduleEditCB(field="poll").pack())],
        [InlineKeyboardButton(text="✏️ Hisobot vaqti", callback_data=OwnerScheduleEditCB(field="report").pack())],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=OwnerPanelCB(section="main").pack())],
    ])


def owner_menu_week_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1-hafta", callback_data=OwnerMenuWeekCB(week=1).pack()),
            InlineKeyboardButton(text="2-hafta", callback_data=OwnerMenuWeekCB(week=2).pack()),
        ],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=OwnerPanelCB(section="main").pack())],
    ])


def owner_menu_day_keyboard(week: int) -> InlineKeyboardMarkup:
    rows = []
    pair = []
    for day in DAY_NAMES:
        pair.append(InlineKeyboardButton(text=DAY_SHORT[day], callback_data=OwnerMenuDayCB(week=week, day=day).pack()))
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=OwnerPanelCB(section="menu_edit").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def owner_menu_day_detail_keyboard(week: int, day: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=OwnerMenuEditStartCB(week=week, day=day).pack())],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=OwnerMenuWeekCB(week=week).pack())],
    ])


def owner_cycle_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for week in (1, 2):
        pair = []
        for day in DAY_NAMES:
            pair.append(InlineKeyboardButton(
                text=f"{week}-{DAY_SHORT[day]}", callback_data=OwnerCycleSetCB(week=week, day=day).pack()
            ))
            if len(pair) == 2:
                rows.append(pair)
                pair = []
        if pair:
            rows.append(pair)
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=OwnerPanelCB(section="main").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)
