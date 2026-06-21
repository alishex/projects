from datetime import date, timedelta
import app.database as db
from app.services.user_service import get_display_name


async def build_order_report(target_date_str: str) -> str:
    """Admin uchun buyurtma hisoboti (to'liq)."""
    from app.services.menu_service import get_menu_for_date
    from datetime import date as dt
    target_date = dt.fromisoformat(target_date_str)
    menu = await get_menu_for_date(target_date)
    if not menu:
        return "Menyu topilmadi."

    users = await db.get_all_active_users()
    orders = await db.get_orders_for_date(target_date_str)
    order_map = {o["telegram_id"]: o for o in orders if o["is_confirmed"] == 1}

    user_map = {u["telegram_id"]: u for u in users}

    def names(ids): return "\n".join(f"{i+1}. {_dn(user_map[uid])}" for i, uid in enumerate(ids)) or "—"
    def _dn(u): return f"@{u['username']}" if u.get("username") else u.get("full_name", f"User_{u['telegram_id']}")

    m1_yes, m1_no = [], []
    m2_yes, m2_no = [], []
    no_answer = []

    for u in users:
        tid = u["telegram_id"]
        if tid not in order_map:
            no_answer.append(tid)
            continue
        o = order_map[tid]
        if o["meal_1_status"] == "yes":
            m1_yes.append(tid)
        else:
            m1_no.append(tid)
        if o["meal_2_status"] == "yes":
            m2_yes.append(tid)
        else:
            m2_no.append(tid)

    lines = [
        f"📋 Ertangi ovqat buyurtma hisoboti\n",
        f"📅 {menu['week_label']}\n",
        f"1-ovqat: {menu['meal_1']}",
        f"Yeydi: {len(m1_yes)} ta | Yemaydi: {len(m1_no)} ta\n",
        f"Yeydiganlar:\n{names(m1_yes)}\n",
        f"Yemaydiganlar:\n{names(m1_no)}\n",
        f"━━━━━━━━━━━━━━━━━━━━\n",
        f"2-ovqat: {menu['meal_2']}",
        f"Yeydi: {len(m2_yes)} ta | Yemaydi: {len(m2_no)} ta\n",
        f"Yeydiganlar:\n{names(m2_yes)}\n",
        f"Yemaydiganlar:\n{names(m2_no)}\n",
    ]
    if no_answer:
        lines.append(f"⚠️ Javob bermaganlar:\n{names(no_answer)}")
    return "\n".join(lines)


async def build_final_report(target_date_str: str) -> str:
    """22:00 da yuboriladi — yakuniy hisobot."""
    from app.services.menu_service import get_menu_for_date
    from datetime import date as dt
    target_date = dt.fromisoformat(target_date_str)
    menu = await get_menu_for_date(target_date)
    if not menu:
        return "Menyu topilmadi."

    users = await db.get_all_active_users()
    orders = await db.get_orders_for_date(target_date_str)
    reports = await db.get_meal_reports_for_date(target_date_str)
    order_map = {o["telegram_id"]: o for o in orders if o["is_confirmed"] == 1}
    user_map = {u["telegram_id"]: u for u in users}

    reported_m1 = {r["telegram_id"] for r in reports if r["meal_number"] == 1}
    reported_m2 = {r["telegram_id"] for r in reports if r["meal_number"] == 2}

    def _dn(u): return f"@{u['username']}" if u.get("username") else u.get("full_name", f"User_{u['telegram_id']}")
    def names(ids): return "\n".join(f"{i+1}. {_dn(user_map[uid])}" for i, uid in enumerate(ids) if uid in user_map) or "—"

    ordered_m1 = [tid for tid, o in order_map.items() if o["meal_1_status"] == "yes"]
    ordered_m2 = [tid for tid, o in order_map.items() if o["meal_2_status"] == "yes"]

    finished_m1 = [tid for tid in ordered_m1 if tid in reported_m1]
    not_fin_m1  = [tid for tid in ordered_m1 if tid not in reported_m1]
    finished_m2 = [tid for tid in ordered_m2 if tid in reported_m2]
    not_fin_m2  = [tid for tid in ordered_m2 if tid not in reported_m2]

    no_answer = [u["telegram_id"] for u in users if u["telegram_id"] not in order_map]

    lines = [
        "📊 Kunlik ovqat yakuniy hisoboti\n",
        f"📅 {menu['week_label']}\n",
        f"1-ovqat: {menu['meal_1']}",
        f"Buyurtma berganlar: {len(ordered_m1)} ta",
        f"Yeb tugatganlar: {len(finished_m1)} ta",
        f"Yemaganlar / video yubormaganlar: {len(not_fin_m1)} ta",
        f"Ortib qolgan ovqat: {max(0, len(ordered_m1) - len(finished_m1))} ta\n",
        f"Yeb tugatganlar:\n{names(finished_m1)}\n",
        f"Yemaganlar / video yubormaganlar:\n{names(not_fin_m1)}\n",
        "━━━━━━━━━━━━━━━━━━━━\n",
        f"2-ovqat: {menu['meal_2']}",
        f"Buyurtma berganlar: {len(ordered_m2)} ta",
        f"Yeb tugatganlar: {len(finished_m2)} ta",
        f"Yemaganlar / video yubormaganlar: {len(not_fin_m2)} ta",
        f"Ortib qolgan ovqat: {max(0, len(ordered_m2) - len(finished_m2))} ta\n",
        f"Yeb tugatganlar:\n{names(finished_m2)}\n",
        f"Yemaganlar / video yubormaganlar:\n{names(not_fin_m2)}\n",
    ]
    if no_answer:
        lines.append(f"⚠️ Tanlov qilmaganlar:\n{names(no_answer)}")
    return "\n".join(lines)
