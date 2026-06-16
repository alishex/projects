from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

remove_keyboard = ReplyKeyboardRemove()


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O‘zbek tili", callback_data="lang:uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский язык", callback_data="lang:ru")],
    ])


def main_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    text = "💼 Bo‘sh ish o‘rinlari" if lang == "uz" else "💼 Вакансии"
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=text)]], resize_keyboard=True)


def vacancy_keyboard(vacancies: list[dict], lang: str = "uz") -> InlineKeyboardMarkup:
    rows = []
    for number, vacancy in enumerate(vacancies, 1):
        label = vacancy.get("name_ru") if lang == "ru" and vacancy.get("name_ru") else vacancy.get("name_uz")
        rows.append([InlineKeyboardButton(text=f"{number}. {label}", callback_data=f"vac:{vacancy['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def start_application_keyboard(vacancy_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    text = "📝 Anketa to‘ldirishni boshlash" if lang == "uz" else "📝 Заполнить анкету"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=f"start_app:{vacancy_id}")]])


def draft_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Davom ettirish", callback_data="draft:continue")],
        [InlineKeyboardButton(text="🆕 Yangi ariza boshlash", callback_data="draft:new")],
    ])


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)


def choice_keyboard(options: list[str], columns: int = 1) -> ReplyKeyboardMarkup:
    rows = []
    for i in range(0, len(options), columns):
        rows.append([KeyboardButton(text=o) for o in options[i:i+columns]])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)


def consent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Roziman", callback_data="consent:yes")],
        [InlineKeyboardButton(text="❌ Rozimasman", callback_data="consent:no")],
    ])


def department_keyboard(vacancies: list[dict], prefix: str = "dept") -> InlineKeyboardMarkup:
    rows = []
    for vacancy in vacancies:
        rows.append([InlineKeyboardButton(text=vacancy.get("name_uz") or "-", callback_data=f"{prefix}:{vacancy['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def followup_unclear_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ishga qabul qilindim", callback_data="fup:accepted")],
        [InlineKeyboardButton(text="❌ Qabul qilinmadim", callback_data="fup:rejected")],
        [InlineKeyboardButton(text="⏳ Hali javob kutyapman", callback_data="fup:waiting")],
    ])
