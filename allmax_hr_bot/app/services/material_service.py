from __future__ import annotations

import json
from datetime import datetime

from app.config import settings
from app.database import db, loads
from app.services.dynamic_service import regulation_text_for_vacancy
from app.services.openai_service import openai_service
from app.utils.texts import LESSON_DAYS


def _day_for(number: int) -> int:
    for day, lessons in LESSON_DAYS.items():
        if number in lessons:
            return day
    return 7


def _fallback_lessons(vacancy: dict, regulation_text: str, count: int = 20) -> list[dict]:
    title = vacancy.get("name_uz") or "Lavozim"
    lines = [x.strip("•- \t") for x in regulation_text.splitlines() if len(x.strip()) > 24 and not x.startswith("===")]
    if not lines:
        lines = ["Tartib-intizom, mas’uliyat, halollik va mijozga hurmat talablariga rioya qilish."]
    lessons = []
    for i in range(1, count + 1):
        focus = lines[(i - 1) % len(lines)]
        lessons.append({
            "lesson_number": i,
            "day_number": _day_for(i),
            "title": f"{i}-dars. {title}: {focus[:55]}",
            "goal": f"{title} ishida reglamentdagi bandni to‘g‘ri tushunish va qo‘llash.",
            "concept": focus,
            "task": "Ushbu qoida ish jarayonida qaysi holatda ishlatilishini amaliy misol bilan yozib chiqing.",
            "attention": "Reglamentdagi talabni o‘zgartirmang; tushunmagan joyingizni rahbardan aniqlashtiring.",
            "remember": focus,
        })
    return lessons


async def generate_lessons(vacancy: dict, regulation_text: str, count: int = 20) -> list[dict]:
    fallback = {"lessons": _fallback_lessons(vacancy, regulation_text, count)}
    system = (
        "Siz ALLMAX stajirovka materiallari yaratuvchi assistentsiz. "
        "Faqat berilgan faol reglament matniga tayaning. Reglamentda bo‘lmagan majburiy qoida o‘ylab topmang. "
        "Har bir darsda goal, concept, task, attention, remember maydonlari bo‘lsin. Faqat JSON qaytaring."
    )
    user = (
        f"Vakansiya: {vacancy.get('name_uz')}\nReglament:\n{regulation_text[:50000]}\n\n"
        f"{count} ta stajirovka darsi yarating. JSON: "
        "{'lessons':[{'lesson_number':1,'day_number':1,'title':'...','goal':'...','concept':'...','task':'...','attention':'...','remember':'...'}]}"
    )
    data = await openai_service.json_chat(system, user, fallback)
    items = data.get("lessons") or fallback["lessons"]
    if len(items) < count:
        return fallback["lessons"]
    out = []
    for i, item in enumerate(items[:count], 1):
        out.append({
            "lesson_number": i,
            "day_number": _day_for(i),
            "title": str(item.get("title") or f"{i}-dars"),
            "goal": str(item.get("goal") or "Mavzuni tushunish."),
            "concept": str(item.get("concept") or "Reglament bandi."),
            "task": str(item.get("task") or "Amalda qo‘llash."),
            "attention": str(item.get("attention") or "Intizomga rioya qiling."),
            "remember": str(item.get("remember") or item.get("concept") or "Reglamentga rioya qiling."),
        })
    return out


async def generate_material_drafts(vacancy_id: int, kinds: set[str], admin_id: int | None) -> dict:
    vacancy = db.get_vacancy(vacancy_id)
    if not vacancy:
        raise ValueError("Vakansiya topilmadi")
    snapshot = db.regulation_snapshot(vacancy_id)
    if not loads(snapshot, []):
        raise ValueError("Ushbu lavozim uchun faol reglament yetarli emas. Avval reglament yuklang va bog‘lang.")
    batch = datetime.now(settings.tz).strftime("%Y%m%d_%H%M%S") + f"_{vacancy_id}"
    created = {"interview": 0, "lessons": 0, "lesson_tests": 0, "final_test": 0, "batch_key": batch}

    if "interview" in kinds:
        reg = regulation_text_for_vacancy(vacancy_id, "interview", snapshot)
        questions = await openai_service.generate_interview_questions(vacancy.get("name_uz") or "", reg, {"source": "admin_template"}, int(vacancy.get("interview_question_count") or 10))
        db.save_training_material(vacancy_id, snapshot, batch, "interview_template", 0, "AI intervyu savollari shabloni", questions, admin_id)
        created["interview"] = len(questions)

    lessons = []
    if "lessons" in kinds or "tests" in kinds:
        if "lessons" in kinds:
            reg = regulation_text_for_vacancy(vacancy_id, "lessons", snapshot)
            lessons = await generate_lessons(vacancy, reg, int(vacancy.get("lesson_count") or 20))
            for lesson in lessons:
                db.save_training_material(vacancy_id, snapshot, batch, "lesson", int(lesson["lesson_number"]), lesson["title"], lesson, admin_id)
            created["lessons"] = len(lessons)
        else:
            existing = db.list_training_materials(vacancy_id, "active", "lesson", 50)
            for item in existing:
                lessons.append(loads(item.get("content"), {}))
            if not lessons:
                reg = regulation_text_for_vacancy(vacancy_id, "lessons", snapshot)
                lessons = await generate_lessons(vacancy, reg, int(vacancy.get("lesson_count") or 20))

    if "tests" in kinds:
        reg = regulation_text_for_vacancy(vacancy_id, "tests", snapshot)
        for lesson in lessons:
            qs = await openai_service.generate_lesson_test(lesson, reg, 10)
            db.save_question_bank(vacancy_id, snapshot, batch, "lesson_test", int(lesson.get("lesson_number") or 0), qs)
            created["lesson_tests"] += len(qs)
        final = await openai_service.generate_final_test(vacancy.get("name_uz") or "", lessons, reg, int(vacancy.get("final_test_count") or 30))
        db.save_question_bank(vacancy_id, snapshot, batch, "final_test", 0, final)
        created["final_test"] = len(final)
    db.change_log(admin_id, "materials_generated", "vacancy", vacancy_id, {}, created)
    return created


def material_summary(vacancy_id: int) -> dict:
    items = db.list_training_materials(vacancy_id, None, None, 500)
    counts: dict[str, dict[str, int]] = {}
    for item in items:
        status = item.get("status") or "draft"
        typ = item.get("material_type") or "-"
        counts.setdefault(typ, {}).setdefault(status, 0)
        counts[typ][status] += 1
    return counts
