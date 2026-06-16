from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from app.config import settings
from app.database import db
from app.states import ResumeFlow
from app.services.dynamic_service import regulation_text_for_vacancy
from app.services.openai_service import openai_service
from app.services.pdf_service import generate_candidate_pdf
from app.utils.texts import LOW_SCORE_MESSAGE, APPLICATION_SENT
from app.utils.validators import h

router = Router()


@router.message(ResumeFlow.interview)
async def interview_answer(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    candidate_id = int(data["candidate_id"])
    interview_id = int(data["ai_interview_id"])
    q_index = int(data.get("q_index") or 0)
    questions = list(data.get("questions") or [])
    if q_index >= len(questions):
        await message.answer("Intervyu yakunlangan.")
        return
    q = questions[q_index]
    answer = (message.text or "").strip()
    if len(answer) < 5:
        await message.answer("Iltimos, javobni biroz to‘liqroq yozing.")
        return
    db.save_ai_answer(interview_id, candidate_id, q, answer)
    q_index += 1
    if q_index < len(questions):
        await state.update_data(q_index=q_index)
        await message.answer(f"{q_index + 1}/{len(questions)}. {questions[q_index]['question']}")
        return

    candidate = db.get_candidate(candidate_id) or {}
    answers = db.ai_answers(interview_id)
    reg = regulation_text_for_vacancy(candidate.get("vacancy_id"), "interview", candidate.get("regulation_version_snapshot"))
    await message.answer("Rahmat. Javoblaringiz tahlil qilinmoqda...")
    evaluation = await openai_service.evaluate_interview(candidate, answers, reg)
    db.save_ai_evaluation(interview_id, candidate_id, evaluation)
    pdf_path = generate_candidate_pdf(candidate_id)

    score = int(evaluation.get("score") or 0)
    if score < 60:
        await message.answer(evaluation.get("polite_candidate_message") or LOW_SCORE_MESSAGE)
    else:
        await message.answer(APPLICATION_SENT)

    candidate = db.get_candidate(candidate_id) or candidate
    duplicate = "\n⚠️ Bu telefon raqam oldin ham ariza bergan." if candidate.get("duplicate_of_candidate_id") else ""
    admin_text = (
        f"📥 <b>Yangi anketa #{candidate_id}</b>{duplicate}\n"
        f"F.I.SH.: <b>{h(candidate.get('full_name'))}</b>\n"
        f"Lavozim: {h(candidate.get('position'))}\n"
        f"Telefon: {h(candidate.get('phone'))}\n"
        f"AI ball: <b>{score}</b> / Grade: {h(evaluation.get('grade'))}\n"
        f"Tavsiya: {h(evaluation.get('admin_recommendation'))}\n"
        f"Xulosa: {h(evaluation.get('summary'))}"
    )
    for admin_id in settings.admin_ids:
        try:
            await message.bot.send_message(admin_id, admin_text)
            await message.bot.send_document(admin_id, FSInputFile(pdf_path), caption=f"PDF anketa #{candidate_id}")
        except Exception:
            pass
    await state.clear()
