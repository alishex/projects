from datetime import date, timedelta
from typing import Optional
import app.database as db
import app.config as cfg

CYCLE_LABELS = [
    (1, "Dushanba"), (1, "Seshanba"), (1, "Chorshanba"), (1, "Payshanba"),
    (1, "Juma"),     (1, "Shanba"),   (1, "Yakshanba"),
    (2, "Dushanba"), (2, "Seshanba"), (2, "Chorshanba"), (2, "Payshanba"),
    (2, "Juma"),     (2, "Shanba"),   (2, "Yakshanba"),
]


def get_cycle_index(target_date: date, anchor_date: str, anchor_index: int) -> int:
    anchor = date.fromisoformat(anchor_date)
    days_diff = (target_date - anchor).days
    return (anchor_index + days_diff) % 14


async def get_menu_for_date(target_date: date) -> Optional[dict]:
    settings = await db.get_settings()
    anchor_date = settings["anchor_date"] if settings else cfg.ANCHOR_DATE
    anchor_index = settings["anchor_index"] if settings else cfg.ANCHOR_INDEX

    idx = get_cycle_index(target_date, anchor_date, anchor_index)
    week_number, day_name = CYCLE_LABELS[idx]
    menu = await db.get_menu_item(week_number, day_name)
    if menu:
        menu["week_label"] = f"{week_number}-hafta {day_name}"
    return menu


async def get_tomorrow_menu() -> Optional[dict]:
    tomorrow = date.today() + timedelta(days=1)
    return await get_menu_for_date(tomorrow)


async def get_today_menu() -> Optional[dict]:
    return await get_menu_for_date(date.today())


def format_menu_text(menu: dict, meal_1_status: Optional[str] = None,
                     meal_2_status: Optional[str] = None) -> str:
    def status_icon(st: Optional[str]) -> str:
        if st == "yes":
            return "✅ "
        if st == "no":
            return "❌ "
        return ""

    m1 = f"{status_icon(meal_1_status)}{menu['meal_1']}"
    m2 = f"{status_icon(meal_2_status)}{menu['meal_2']}"
    return (
        f"🍽 Ertangi taomnoma\n\n"
        f"📅 {menu['week_label']}\n\n"
        f"1-ovqat: {m1}\n"
        f"2-ovqat: {m2}"
    )
