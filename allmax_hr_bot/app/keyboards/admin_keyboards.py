from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

ADMIN_SECTIONS = [
    ("new", "1. Yangi arizalar"),
    ("ai_rejected", "2. AI rad etganlar"),
    ("medium", "3. O‘rta baho: 60–79"),
    ("excellent", "4. A’lo baho: 80–100"),
    ("invited", "5. Intervyuga chaqirilganlar"),
    ("accepted", "6. Qabul qilinganlar"),
    ("rejected", "7. Ishga qabul qilinmaganlar"),
    ("onboarding", "8. Stajirovkadagilar"),
    ("employees", "9. Xodimlar bazasi"),
    ("export", "10. Excel eksport"),
    ("stats", "11. Statistika"),
    ("progress", "12. Dars progressi"),
    ("finals", "13. Yakuniy test natijalari"),
    ("clockster", "14. Clockster nazorat"),
]


def admin_main_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="⚙️ Dinamik vakansiya va reglament boshqaruvi", callback_data="dyn:home")]]
    for i in range(0, len(ADMIN_SECTIONS), 2):
        rows.append([InlineKeyboardButton(text=t, callback_data=f"adm_sec:{k}") for k, t in ADMIN_SECTIONS[i:i+2]])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def candidates_list_keyboard(candidates: list[dict], section: str) -> InlineKeyboardMarkup:
    rows = []
    for c in candidates:
        rows.append([InlineKeyboardButton(text=f"#{c['id']} {c.get('full_name') or '-'} — {c.get('position') or '-'}", callback_data=f"adm_c:{c['id']}")])
    rows.append([InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def candidate_card_keyboard(candidate_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 PDF anketani olish", callback_data=f"adm_pdf:{candidate_id}"), InlineKeyboardButton(text="🤖 AI xulosasi", callback_data=f"adm_ai:{candidate_id}")],
        [InlineKeyboardButton(text="📅 Intervyuga chaqirish", callback_data=f"adm_inv:{candidate_id}"), InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"adm_acc:{candidate_id}")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"adm_rej:{candidate_id}"), InlineKeyboardButton(text="🗂 Zaxiraga olish", callback_data=f"adm_res:{candidate_id}")],
        [InlineKeyboardButton(text="📝 Admin izohi", callback_data=f"adm_note:{candidate_id}"), InlineKeyboardButton(text="📊 Excel eksport", callback_data="adm_sec:export")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm:home")],
    ])


def admin_department_keyboard(candidate_id: int, vacancies: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for vacancy in vacancies:
        rows.append([InlineKeyboardButton(text=vacancy.get("name_uz") or "-", callback_data=f"adm_dept:{candidate_id}:{vacancy['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:home")]])


def clockster_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Clockster sync hozir", callback_data="clk:sync")],
        [InlineKeyboardButton(text="👥 Xodimlar kelib-ketishi", callback_data="clk:list")],
        [InlineKeyboardButton(text="🧾 Oxirgi sync loglar", callback_data="clk:logs")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:home")],
    ])


def clockster_employee_keyboard(employees: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for e in employees[:30]:
        rows.append([InlineKeyboardButton(text=f"#{e['id']} {e.get('full_name') or '-'}", callback_data=f"clk:e:{e['id']}")])
    rows.append([InlineKeyboardButton(text="⬅️ Clockster", callback_data="adm_sec:clockster")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
