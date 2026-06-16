from __future__ import annotations

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.database import db, loads
from app.services.dynamic_service import regulation_text_for_vacancy
from app.utils.texts import LESSON_DAYS
from app.utils.validators import h, chunk_text


def day_for_lesson(lesson_number: int) -> int:
    for day, lessons in LESSON_DAYS.items():
        if lesson_number in lessons:
            return day
    return 7


def lesson_payload(department: str, lesson_number: int, regulation_text: str) -> dict:
    lines = [ln.strip("•- ").strip() for ln in regulation_text.splitlines() if len(ln.strip()) > 25 and not ln.startswith("===")]
    if not lines:
        lines = ["ALLMAXda tartib-intizom, mas’uliyat, halollik va mijozga hurmat asosiy qadriyat hisoblanadi."]
    block = lines[(lesson_number - 1) % len(lines)]
    return {
        "goal": f"{department} bo‘yicha {lesson_number}-mavzuni tushunish va amalda qo‘llash.",
        "concept": block,
        "task": "Bugungi mavzu bo‘yicha real ish jarayonidan bitta misol yozing.",
        "attention": "Reglamentdan chetga chiqmaslik va tushunmagan joyni mas’ul shaxsdan so‘rash kerak.",
        "remember": block,
    }


def ensure_lessons(employee_id: int) -> None:
    employee = db.get_employee(employee_id)
    if not employee:
        return
    dept = employee.get("department") or "ALLMAX"
    vacancy_id = int(employee.get("vacancy_id") or 0)
    snapshot = employee.get("regulation_version_snapshot")
    lesson_count = int((db.get_vacancy(vacancy_id) or {}).get("lesson_count") or 20)
    reg = regulation_text_for_vacancy(vacancy_id, "lessons", snapshot)
    for n in range(1, lesson_count + 1):
        template = db.active_material(vacancy_id, "lesson", n, snapshot) if vacancy_id else None
        if template:
            payload = loads(template.get("content"), {})
            title = payload.get("title") or template.get("title") or f"{n}-dars: {dept}"
        else:
            payload = lesson_payload(dept, n, reg)
            title = f"{n}-dars: {dept} reglamenti"
        lesson_id = db.upsert_lesson(employee_id, dept, n, day_for_lesson(n), title, payload)
        with db.connect() as conn:
            conn.execute("UPDATE onboarding_lessons SET vacancy_id=?, regulation_version_snapshot=?, training_material_id=? WHERE id=?", (vacancy_id or None, snapshot, template.get("id") if template else None, lesson_id))
            conn.execute("UPDATE onboarding_progress SET vacancy_id=?, regulation_version_snapshot=? WHERE employee_id=? AND lesson_number=?", (vacancy_id or None, snapshot, employee_id, n))
            conn.commit()


def current_lesson_number(employee_id: int) -> int:
    employee = db.get_employee(employee_id) or {}
    lesson_count = int((db.get_vacancy(int(employee.get("vacancy_id") or 0)) or {}).get("lesson_count") or 20)
    for n in range(1, lesson_count + 1):
        progress = db.lesson_progress(employee_id, n)
        if not progress or progress.get("status") != "completed":
            return n
    return lesson_count + 1


def lesson_keyboard(employee_id: int, lesson_number: int, started: bool = False) -> InlineKeyboardMarkup:
    button = "✅ Darsni tugatdim" if started else "✅ Darsni boshlash"
    prefix = "les_done" if started else "les_start"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=button, callback_data=f"{prefix}:{employee_id}:{lesson_number}")]])


def test_keyboard(test_id: int, question_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="A", callback_data=f"lt:{test_id}:{question_number}:A"), InlineKeyboardButton(text="B", callback_data=f"lt:{test_id}:{question_number}:B")],
        [InlineKeyboardButton(text="C", callback_data=f"lt:{test_id}:{question_number}:C"), InlineKeyboardButton(text="D", callback_data=f"lt:{test_id}:{question_number}:D")],
    ])


def final_keyboard(final_id: int, question_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="A", callback_data=f"ft:{final_id}:{question_number}:A"), InlineKeyboardButton(text="B", callback_data=f"ft:{final_id}:{question_number}:B")],
        [InlineKeyboardButton(text="C", callback_data=f"ft:{final_id}:{question_number}:C"), InlineKeyboardButton(text="D", callback_data=f"ft:{final_id}:{question_number}:D")],
    ])


def render_lesson(lesson: dict) -> str:
    c = lesson.get("content") or {}
    return (
        f"📘 <b>{h(lesson.get('title'))}</b>\n"
        f"<b>Kun:</b> {h(lesson.get('day_number'))} | <b>Dars:</b> {h(lesson.get('lesson_number'))}\n\n"
        f"🎯 <b>Dars maqsadi</b>\n{h(c.get('goal'))}\n\n"
        f"📘 <b>Asosiy tushuncha</b>\n{h(c.get('concept'))}\n\n"
        f"✅ <b>Amaliy vazifa</b>\n{h(c.get('task') or c.get('practice'))}\n\n"
        f"⚠️ <b>E’tibor berish kerak</b>\n{h(c.get('attention') or c.get('warning'))}\n\n"
        f"🧠 <b>Eslab qolish kerak</b>\n{h(c.get('remember'))}"
    )


async def send_current_lesson(bot: Bot, user_id: int, employee_id: int) -> None:
    ensure_lessons(employee_id)
    employee = db.get_employee(employee_id) or {}
    lesson_count = int((db.get_vacancy(int(employee.get("vacancy_id") or 0)) or {}).get("lesson_count") or 20)
    n = current_lesson_number(employee_id)
    if n > lesson_count:
        await bot.send_message(user_id, "Siz barcha darslarni tugatdingiz. Endi yakuniy test boshlanadi.")
        return
    lesson = db.get_lesson(employee_id, n)
    if not lesson:
        await bot.send_message(user_id, "Dars topilmadi. Admin bilan bog‘laning.")
        return
    parts = chunk_text(render_lesson(lesson))
    for index, part in enumerate(parts):
        await bot.send_message(user_id, part, reply_markup=lesson_keyboard(employee_id, n, started=False) if index == len(parts) - 1 else None)


async def notify_admins(bot: Bot, text: str) -> None:
    from app.config import settings
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass
