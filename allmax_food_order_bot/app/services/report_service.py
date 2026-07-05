from app.config import DEPARTMENTS


def build_owner_report(date_display: str, meal1_name: str, meal2_name: str,
                        orders: list[dict]) -> str:
    orders_by_dept = {o["dept_key"]: o for o in orders}

    def count(dept_key: str, meal: int) -> int:
        o = orders_by_dept.get(dept_key)
        if not o:
            return 0
        return o["meal1_count"] if meal == 1 else o["meal2_count"]

    meal1_rows = ""
    meal1_total = 0
    meal2_rows = ""
    meal2_total = 0

    for dept in DEPARTMENTS:
        m1 = count(dept["key"], 1)
        m2 = count(dept["key"], 2)
        meal1_total += m1
        meal2_total += m2
        meal1_rows += f"{dept['emoji']} {dept['name']:<18} →  {m1:>3} ta\n"
        meal2_rows += f"{dept['emoji']} {dept['name']:<18} →  {m2:>3} ta\n"

    grand_total = meal1_total + meal2_total

    return (
        f"🍽 <b>Ovqat buyurtmasi hisoboti</b>\n"
        f"📅 {date_display}\n\n"
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
