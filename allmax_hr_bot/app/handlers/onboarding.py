from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.database import db, now_str
from app.services.dynamic_service import regulation_text_for_vacancy
from app.services.lesson_service import test_keyboard, final_keyboard, send_current_lesson, notify_admins
from app.services.openai_service import openai_service
from app.services.clockster_service import sync_employee_attendance
from app.utils.validators import h

router = Router()


def _render_question(prefix: str, number: int, total: int, q: dict) -> str:
    opts = q.get("options") or {}
    return (
        f"{prefix} <b>{number}/{total}</b>\n\n"
        f"{h(q.get('question'))}\n\n"
        f"A) {h(opts.get('A'))}\n"
        f"B) {h(opts.get('B'))}\n"
        f"C) {h(opts.get('C'))}\n"
        f"D) {h(opts.get('D'))}"
    )


@router.callback_query(F.data.startswith("les_start:"))
async def lesson_start(callback: CallbackQuery) -> None:
    await callback.answer()
    _, employee_id, lesson_number = (callback.data or "les_start:0:1").split(":")
    employee_id, lesson_number = int(employee_id), int(lesson_number)
    db.update_lesson_progress(employee_id, lesson_number, status="started", started_at=now_str())
    from app.services.lesson_service import lesson_keyboard
    await callback.message.answer("Dars boshlandi. O‘qib bo‘lgach pastdagi tugmani bosing.", reply_markup=lesson_keyboard(employee_id, lesson_number, started=True))


@router.callback_query(F.data.startswith("les_done:"))
async def lesson_done(callback: CallbackQuery) -> None:
    await callback.answer()
    _, employee_id, lesson_number = (callback.data or "les_done:0:1").split(":")
    employee_id, lesson_number = int(employee_id), int(lesson_number)
    lesson = db.get_lesson(employee_id, lesson_number)
    employee = db.get_employee(employee_id)
    if not lesson or not employee:
        await callback.message.answer("Dars yoki xodim topilmadi.")
        return
    vacancy_id = int(employee.get("vacancy_id") or 0)
    snapshot = employee.get("regulation_version_snapshot")
    questions = db.active_questions(vacancy_id, "lesson_test", lesson_number, snapshot) if vacancy_id else []
    if not questions:
        reg = regulation_text_for_vacancy(vacancy_id, "tests", snapshot)
        questions = await openai_service.generate_lesson_test(lesson, reg, count=10)
    test_id = db.create_lesson_test(employee_id, lesson_number, questions)
    with db.connect() as conn:
        conn.execute("UPDATE lesson_tests SET vacancy_id=?, regulation_version_snapshot=? WHERE id=?", (vacancy_id or None, snapshot, test_id))
        conn.commit()
    await callback.message.answer("Dars testi boshlandi. Har savolda bitta javobni tanlang.")
    await callback.message.answer(_render_question("🧪 Dars testi", 1, len(questions), questions[0]), reply_markup=test_keyboard(test_id, 1))


@router.callback_query(F.data.startswith("lt:"))
async def lesson_test_answer(callback: CallbackQuery) -> None:
    await callback.answer()
    _, test_id, qn, selected = (callback.data or "lt:0:1:A").split(":")
    test_id, qn = int(test_id), int(qn)
    result = db.save_lesson_test_answer(test_id, qn, selected)
    test = db.get_lesson_test(test_id)
    if not test:
        return
    if result.get("completed"):
        percent = float(result.get("percent") or 0)
        msg = f"Natija: <b>{result.get('correct_count')}/{result.get('total')}</b> — <b>{percent}%</b>. "
        if percent < 60:
            msg += "Mavzuni qayta o‘qishni maslahat beramiz. Admin panelda ogohlantirish chiqadi."
            await notify_admins(callback.message.bot, f"⚠️ Dars testi past: employee #{test['employee_id']}, dars {test['lesson_number']}, natija {percent}%")
        elif percent > 80:
            msg += "Ajoyib! Mavzuni yaxshi tushundingiz."
            await notify_admins(callback.message.bot, f"✅ Yaxshi progress: employee #{test['employee_id']}, dars {test['lesson_number']}, natija {percent}%")
        else:
            msg += "Yaxshi, lekin ayrim joylarni yana mustahkamlang."
        await callback.message.answer(msg)
        employee = db.get_employee(int(test["employee_id"])) or {}
        lesson_count = int((db.get_vacancy(int(employee.get("vacancy_id") or 0)) or {}).get("lesson_count") or 20)
        if int(test["lesson_number"]) >= lesson_count:
            await start_final_test(callback, int(test["employee_id"]))
        else:
            await send_current_lesson(callback.message.bot, int(employee["telegram_id"]), int(test["employee_id"]))
        return
    next_q = qn + 1
    questions = test["questions"]
    await callback.message.answer(_render_question("🧪 Dars testi", next_q, len(questions), questions[next_q - 1]), reply_markup=test_keyboard(test_id, next_q))


async def start_final_test(callback: CallbackQuery, employee_id: int) -> None:
    employee = db.get_employee(employee_id)
    if not employee:
        return
    vacancy_id = int(employee.get("vacancy_id") or 0)
    snapshot = employee.get("regulation_version_snapshot")
    vacancy = db.get_vacancy(vacancy_id) or {}
    lesson_count = int(vacancy.get("lesson_count") or 20)
    final_count = int(vacancy.get("final_test_count") or 30)
    questions = db.active_questions(vacancy_id, "final_test", 0, snapshot) if vacancy_id else []
    if not questions:
        lessons = [db.get_lesson(employee_id, i) for i in range(1, lesson_count + 1)]
        lessons = [x for x in lessons if x]
        reg = regulation_text_for_vacancy(vacancy_id, "tests", snapshot)
        questions = await openai_service.generate_final_test(employee.get("department") or "", lessons, reg, final_count)
    questions = questions[:final_count]
    final_id = db.create_final_test(employee_id, employee.get("department") or "", questions)
    with db.connect() as conn:
        conn.execute("UPDATE final_tests SET vacancy_id=?, regulation_version_snapshot=?, total_questions=? WHERE id=?", (vacancy_id or None, snapshot, len(questions), final_id))
        conn.commit()
    await callback.message.answer(f"🏁 Yakuniy {len(questions)} talik test boshlandi.")
    await callback.message.answer(_render_question("🏁 Yakuniy test", 1, len(questions), questions[0]), reply_markup=final_keyboard(final_id, 1))


@router.callback_query(F.data.startswith("ft:"))
async def final_test_answer(callback: CallbackQuery) -> None:
    await callback.answer()
    _, final_id, qn, selected = (callback.data or "ft:0:1:A").split(":")
    final_id, qn = int(final_id), int(qn)
    result = db.save_final_test_answer(final_id, qn, selected)
    final = db.get_final_test(final_id)
    if not final:
        return
    if result.get("completed"):
        employee = db.get_employee(int(final["employee_id"])) or {}
        stats = db.lesson_test_stats(int(final["employee_id"]))
        evaluation = await openai_service.evaluate_final(employee, stats, db.get_final_test(final_id) or final)
        db.save_final_evaluation(final_id, evaluation)
        percent = float(result.get("percent") or 0)

        # Clockster monitoring is intentionally connected only after internship and final test completion.
        clockster_result = await sync_employee_attendance(int(final["employee_id"]))
        clockster_note = clockster_result.get("message") or "Clockster sync natijasi noma’lum."

        await callback.message.answer(f"Yakuniy test natijangiz: <b>{result.get('correct_count')}/{result.get('total')}</b> — <b>{percent}%</b>. Tabriklaymiz, stajirovka testini yakunladingiz.")
        await notify_admins(
            callback.message.bot,
            f"🏁 Yakuniy test yakunlandi\n"
            f"Xodim: {h(employee.get('full_name'))}\n"
            f"Bo‘lim: {h(employee.get('department'))}\n"
            f"Natija: {result.get('correct_count')}/{result.get('total')} — {percent}%\n"
            f"{h(evaluation.get('message_to_admin'))}\n\n"
            f"🕒 Clockster: {h(clockster_note)}",
        )
        return
    next_q = qn + 1
    questions = final["questions"]
    await callback.message.answer(_render_question("🏁 Yakuniy test", next_q, len(questions), questions[next_q - 1]), reply_markup=final_keyboard(final_id, next_q))
