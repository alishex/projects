from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def dynamic_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Vakansiyalarni boshqarish", callback_data="dyn:vac"), InlineKeyboardButton(text="📚 Reglamentlarni boshqarish", callback_data="dyn:reg")],
        [InlineKeyboardButton(text="🔗 Vakansiya va reglament bog‘lash", callback_data="dyn:link"), InlineKeyboardButton(text="🧠 AI materiallarni yaratish", callback_data="dyn:ai")],
        [InlineKeyboardButton(text="📦 Reglament versiyalari", callback_data="dyn:versions"), InlineKeyboardButton(text="📊 Dars va test materiallari", callback_data="dyn:mats")],
        [InlineKeyboardButton(text="📝 O‘zgarishlar tarixi", callback_data="dyn:logs")],
        [InlineKeyboardButton(text="⬅️ Asosiy admin panel", callback_data="adm:home")],
    ])


def vacancy_manage_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi vakansiya qo‘shish", callback_data="dyn:vnew")],
        [InlineKeyboardButton(text="✏️ Mavjud vakansiyani tahrirlash", callback_data="dyn:vedit"), InlineKeyboardButton(text="👁 Vakansiyalar ro‘yxati", callback_data="dyn:vlist")],
        [InlineKeyboardButton(text="🔴 Vakansiyani yashirish", callback_data="dyn:vstatus:hidden"), InlineKeyboardButton(text="🟢 Vakansiyani faollashtirish", callback_data="dyn:vstatus:active")],
        [InlineKeyboardButton(text="🗄 Vakansiyani arxivlash", callback_data="dyn:vstatus:archived")],
        [InlineKeyboardButton(text="⬅️ Dinamik boshqaruv", callback_data="dyn:home")],
    ])


def regulations_manage_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi reglament yuklash", callback_data="dyn:rnew")],
        [InlineKeyboardButton(text="🔄 Reglamentni yangilash", callback_data="dyn:rupd"), InlineKeyboardButton(text="📖 Reglamentlar ro‘yxati", callback_data="dyn:rlist")],
        [InlineKeyboardButton(text="📦 Versiyalarni ko‘rish", callback_data="dyn:versions"), InlineKeyboardButton(text="↩️ Oldingi versiyaga qaytish", callback_data="dyn:rrollback")],
        [InlineKeyboardButton(text="🗄 Reglamentni arxivlash", callback_data="dyn:rarchive")],
        [InlineKeyboardButton(text="⬅️ Dinamik boshqaruv", callback_data="dyn:home")],
    ])


def vacancies_keyboard(vacancies: list[dict], prefix: str, include_status: bool = True) -> InlineKeyboardMarkup:
    rows = []
    for v in vacancies[:60]:
        text = f"{v['name_uz']}" + (f" — {str(v.get('status')).title()}" if include_status else "")
        rows.append([InlineKeyboardButton(text=text[:55], callback_data=f"{prefix}:{v['id']}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="dyn:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def regulations_keyboard(regulations: list[dict], prefix: str) -> InlineKeyboardMarkup:
    rows = []
    for r in regulations[:60]:
        version = f"v{r.get('current_version_number')}" if r.get('current_version_number') else "versiyasiz"
        rows.append([InlineKeyboardButton(text=f"{r['title'][:38]} — {version}", callback_data=f"{prefix}:{r['id']}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="dyn:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def yes_no_keyboard(yes_callback: str, no_callback: str = "dyn:home") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=yes_callback), InlineKeyboardButton(text="❌ Bekor qilish", callback_data=no_callback)]])


def vacancy_status_keyboard(vacancy_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Active", callback_data=f"dyn:vset:{vacancy_id}:active"), InlineKeyboardButton(text="🔴 Hidden", callback_data=f"dyn:vset:{vacancy_id}:hidden")],
        [InlineKeyboardButton(text="🗄 Archived", callback_data=f"dyn:vconfirmarc:{vacancy_id}"), InlineKeyboardButton(text="📝 Draft", callback_data=f"dyn:vset:{vacancy_id}:draft")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="dyn:vac")],
    ])


def vacancy_edit_fields_keyboard(vacancy_id: int) -> InlineKeyboardMarkup:
    fields = [("name_uz", "Nomi UZ"), ("name_ru", "Nomi RU"), ("description_uz", "Tavsif"), ("responsibilities", "Vazifalar"), ("requirements", "Talablar"), ("work_schedule", "Ish grafigi"), ("interview_question_count", "Intervyu savollar soni"), ("internship_days", "Stajirovka kuni"), ("lesson_count", "Dars soni"), ("final_test_count", "Final test soni")]
    rows=[]
    for i in range(0, len(fields), 2):
        rows.append([InlineKeyboardButton(text=label, callback_data=f"dyn:vef:{vacancy_id}:{key}") for key,label in fields[i:i+2]])
    rows.append([InlineKeyboardButton(text="Statusini o‘zgartirish", callback_data=f"dyn:vshowstatus:{vacancy_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="dyn:vac")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def schedule_choices_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="To‘liq stavka", callback_data="dyn:vsch:To‘liq stavka"), InlineKeyboardButton(text="Yarim stavka", callback_data="dyn:vsch:Yarim stavka")],
        [InlineKeyboardButton(text="Kelishuv asosida", callback_data="dyn:vsch:Kelishuv asosida")],
        [InlineKeyboardButton(text="✍️ O‘zim yozaman", callback_data="dyn:vsch:custom")],
    ])


def visibility_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Faol qilish", callback_data="dyn:vvis:active"), InlineKeyboardButton(text="⏸ Hozircha yashirish", callback_data="dyn:vvis:hidden")],
    ])


def after_vacancy_keyboard(vacancy_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Hozir reglament biriktirish", callback_data=f"dyn:linksel:{vacancy_id}"), InlineKeyboardButton(text="⏭ Keyinroq", callback_data="dyn:vac")],
    ])


def regulation_type_keyboard() -> InlineKeyboardMarkup:
    names = ["Asosiy lavozim", "Xavfsizlik", "Umumiy qadriyatlar", "Ish grafigi", "Mahsulot standarti", "Kontent standarti", "Qo‘shimcha qoida"]
    rows=[]
    for i, label in enumerate(names):
        rows.append([InlineKeyboardButton(text=label, callback_data=f"dyn:rtype:{i}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def multi_vacancy_select_keyboard(vacancies: list[dict], selected: set[int]) -> InlineKeyboardMarkup:
    rows=[]
    for v in vacancies[:40]:
        mark="✅" if int(v['id']) in selected else "▫️"
        rows.append([InlineKeyboardButton(text=f"{mark} {v['name_uz']}", callback_data=f"dyn:rvsel:{v['id']}")])
    rows.append([InlineKeyboardButton(text="➕ Yangi vakansiya qo‘shish", callback_data="dyn:vnew")])
    rows.append([InlineKeyboardButton(text="➡️ Davom etish", callback_data="dyn:rfile")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_regulation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Faollashtirish", callback_data="dyn:ractivate"), InlineKeyboardButton(text="✏️ Qayta yuklash", callback_data="dyn:rfile")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="dyn:home")],
    ])


def version_keyboard(versions: list[dict], prefix: str) -> InlineKeyboardMarkup:
    rows=[]
    for v in versions:
        mark="✅" if v.get('is_active') else "▫️"
        rows.append([InlineKeyboardButton(text=f"{mark} v{v['version_number']} — {v.get('original_filename') or '-'}"[:56], callback_data=f"{prefix}:{v['id']}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="dyn:versions")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def link_regulation_keyboard(regulations: list[dict], vacancy_id: int, linked_ids: set[int]) -> InlineKeyboardMarkup:
    rows=[]
    for r in regulations:
        mark="✅" if int(r['id']) in linked_ids else "▫️"
        rows.append([InlineKeyboardButton(text=f"{mark} {r['title'][:42]}", callback_data=f"dyn:togglelink:{vacancy_id}:{r['id']}")])
    rows.append([InlineKeyboardButton(text="✅ Saqlash / yakunlash", callback_data="dyn:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def material_actions_keyboard(vacancy_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Hammasini qayta yaratish", callback_data=f"dyn:gen:{vacancy_id}:all")],
        [InlineKeyboardButton(text="🧠 Faqat intervyu", callback_data=f"dyn:gen:{vacancy_id}:interview"), InlineKeyboardButton(text="📘 Faqat darslar", callback_data=f"dyn:gen:{vacancy_id}:lessons")],
        [InlineKeyboardButton(text="📝 Faqat testlar", callback_data=f"dyn:gen:{vacancy_id}:tests"), InlineKeyboardButton(text="⏭ Yangilamaslik", callback_data="dyn:home")],
    ])


def batch_activate_keyboard(vacancy_id: int, batch_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash va faollashtirish", callback_data=f"dyn:mactivate:{vacancy_id}:{batch_key}")],
        [InlineKeyboardButton(text="🔄 Qayta yaratish", callback_data=f"dyn:ai_v:{vacancy_id}"), InlineKeyboardButton(text="❌ Hozircha draft", callback_data="dyn:home")],
    ])
