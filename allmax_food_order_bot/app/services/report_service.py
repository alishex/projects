import logging

import app.config as cfg

logger = logging.getLogger(__name__)


def build_owner_report(date_display: str, meal1_name: str, meal2_name: str,
                        orders: list[dict]) -> str:
    orders_by_dept = {o["dept_key"]: o for o in orders}
    known_keys = {d["key"] for d in cfg.DEPARTMENTS}

    unknown_keys = set(orders_by_dept) - known_keys
    if unknown_keys:
        logger.warning(f"build_owner_report: bo'limlar ro'yxatida yo'q dept_key(lar) topildi: {unknown_keys}")

    # Owner panel orqali o'chirilgan/o'zgartirilgan bo'limlarga tegishli
    # (tarixiy) buyurtmalar ham hisobotdan tushib qolmasligi uchun qo'shamiz.
    all_depts = list(cfg.DEPARTMENTS) + [
        {"key": key, "name": key, "emoji": "❓"} for key in sorted(unknown_keys)
    ]

    meal1_rows = ""
    meal1_total = 0
    meal2_rows = ""
    meal2_total = 0
    missing = []

    for dept in all_depts:
        order = orders_by_dept.get(dept["key"])
        if order is None:
            missing.append(dept["name"])
            meal1_rows += f"{dept['emoji']} {dept['name']:<18} →  javob yo'q\n"
            meal2_rows += f"{dept['emoji']} {dept['name']:<18} →  javob yo'q\n"
            continue
        m1 = order["meal1_count"]
        m2 = order["meal2_count"]
        tag = " (owner)" if order.get("admin_id") in cfg.OWNER_IDS else ""
        meal1_total += m1
        meal2_total += m2
        meal1_rows += f"{dept['emoji']} {dept['name']:<18} →  {m1:>3} ta{tag}\n"
        meal2_rows += f"{dept['emoji']} {dept['name']:<18} →  {m2:>3} ta{tag}\n"

    grand_total = meal1_total + meal2_total
    warning = f"⚠️ <b>Javob bermagan bo'limlar:</b> {', '.join(missing)}\n\n" if missing else ""

    return (
        f"🍽 <b>Ovqat buyurtmasi hisoboti</b>\n"
        f"📅 {date_display}\n\n"
        f"{warning}"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🥘 <b>TUSHLIK:</b> {meal1_name}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<code>{meal1_rows}</code>"
        f"─────────────────────────\n"
        f"📊 <b>Jami tushlik: {meal1_total} ta</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌙 <b>KECHKI OVQAT:</b> {meal2_name}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<code>{meal2_rows}</code>"
        f"─────────────────────────\n"
        f"📊 <b>Jami kechki: {meal2_total} ta</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🍱 <b>UMUMIY JAMI: {grand_total} ta</b>"
    )
