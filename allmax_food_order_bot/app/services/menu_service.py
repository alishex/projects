from datetime import date, timedelta
from typing import Optional
import app.database as db
from app.config import ANCHOR_DATE, ANCHOR_INDEX

CYCLE_LABELS = [
    (1, "Dushanba"), (1, "Seshanba"), (1, "Chorshanba"), (1, "Payshanba"),
    (1, "Juma"),     (1, "Shanba"),   (1, "Yakshanba"),
    (2, "Dushanba"), (2, "Seshanba"), (2, "Chorshanba"), (2, "Payshanba"),
    (2, "Juma"),     (2, "Shanba"),   (2, "Yakshanba"),
]

UZ_MONTHS = [
    "", "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"
]
UZ_DAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]


def format_date_uz(d: date) -> str:
    return f"{d.day}-{UZ_MONTHS[d.month]}, {UZ_DAYS[d.weekday()]}"


async def get_menu_for_date(target_date: date) -> Optional[dict]:
    settings = await db.get_settings()
    anchor_date = settings.get("anchor_date", ANCHOR_DATE)
    anchor_index = settings.get("anchor_index", ANCHOR_INDEX)

    anchor = date.fromisoformat(anchor_date)
    days_diff = (target_date - anchor).days
    idx = (int(anchor_index) + days_diff) % 14
    week_number, day_name = CYCLE_LABELS[idx]

    menu = await db.get_menu_item(week_number, day_name)
    if menu:
        menu["date_str"] = target_date.isoformat()
        menu["date_display"] = format_date_uz(target_date)
    return menu


async def get_tomorrow_menu() -> Optional[dict]:
    return await get_menu_for_date(date.today() + timedelta(days=1))
