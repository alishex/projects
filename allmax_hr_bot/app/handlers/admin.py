from __future__ import annotations

from datetime import timedelta
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.database import db
from app.keyboards.admin_keyboards import admin_main_keyboard, candidates_list_keyboard, candidate_card_keyboard, admin_department_keyboard, back_admin_keyboard, clockster_keyboard, clockster_employee_keyboard
from app.services.pdf_service import generate_candidate_pdf
from app.services.excel_service import export_candidates_excel
from app.services.scheduler_service import parse_interview_input, schedule_followup
from app.services.lesson_service import ensure_lessons, send_current_lesson
from app.services.clockster_service import sync_all_clockster_attendance
from app.states import AdminFlow
from app.utils.validators import h

router = Router()


def admin_only(user_id: int) -> bool:
    return db.is_admin(user_id)


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if not admin_only(message.from_user.id):
        await message.answer("Sizda admin panelga kirish huquqi yo‘q.")
        return
    await message.answer("ALLMAX HR admin panel", reply_markup=admin_main_keyboard())


@router.callback_query(F.data == "adm:home")
async def admin_home(callback: CallbackQuery) -> None:
    await callback.answer()
    if not admin_only(callback.from_user.id):
        return
    await callback.message.answer("ALLMAX HR admin panel", reply_markup=admin_main_keyboard())


@router.callback_query(F.data.startswith("adm_sec:"))
async def admin_section(callback: CallbackQuery) -> None:
    await callback.answer()
    if not admin_only(callback.from_user.id):
        return
    section = (callback.data or "").split(":", 1)[1]
    if section == "export":
        path = export_candidates_excel()
        await callback.message.answer_document(FSInputFile(path), caption="Excel eksport tayyor.")
        return
    if section == "stats":
        s = db.stats()
        await callback.message.answer(
            "📊 <b>Statistika</b>\n" + "\n".join(f"{h(k)}: <b>{h(v)}</b>" for k, v in s.items()),
            reply_markup=back_admin_keyboard(),
        )
        return
    if section == "clockster":
        rows = db.clockster_dashboard(limit=10)
        lines = ["🕒 <b>Clockster kelib-ketish nazorati</b>"]
        if not rows:
            lines.append("Xodimlar bazasi bo‘sh.")
        for e in rows:
            latest = e.get("latest_attendance") or {}
            link = e.get("clockster_employee_id") or "bog‘lanmagan"
            lines.append(
                f"#{e['id']} {h(e.get('full_name'))} — {h(e.get('department'))}\n"
                f"Clockster: {h(link)} | Sync: {h(e.get('clockster_last_sync_at') or '-')}\n"
                f"Keldi: {h(latest.get('check_in') or '-')} | Ketdi: {h(latest.get('check_out') or '-')} | Status: {h(latest.get('status') or '-')}"
            )
        await callback.message.answer("\n\n".join(lines), reply_markup=clockster_keyboard())
        return
    if section in {"employees", "onboarding", "progress"}:
        employees = db.list_employees(status="onboarding" if section in {"onboarding", "progress"} else None, limit=30)
        if not employees:
            await callback.message.answer("Xodimlar topilmadi.", reply_markup=back_admin_keyboard())
            return
        lines = ["👥 <b>Xodimlar</b>"]
        for e in employees:
            tests = db.lesson_test_stats(e["id"])
            avg = round(sum(float(t.get("percentage") or 0) for t in tests) / len(tests), 1) if tests else 0
            clk = e.get("clockster_sync_status") or "clockster:-"
            lines.append(f"#{e['id']} {h(e.get('full_name'))} — {h(e.get('department'))} | Dars: {db.completed_lessons_count(e['id'])}/20 | Avg: {avg}% | {h(clk)}")
        await callback.message.answer("\n".join(lines), reply_markup=back_admin_keyboard())
        return
    if section == "finals":
        finals = db.final_tests(limit=30)
        if not finals:
            await callback.message.answer("Yakuniy test natijalari topilmadi.", reply_markup=back_admin_keyboard())
            return
        lines = ["🏁 <b>Yakuniy test natijalari</b>"]
        for f in finals:
            lines.append(f"#{f['id']} employee:{f.get('employee_id')} | {h(f.get('department'))} | {f.get('correct_answers')}/{f.get('total_questions')} — {f.get('percentage')}% | {h(f.get('admin_recommendation'))}")
        await callback.message.answer("\n".join(lines), reply_markup=back_admin_keyboard())
        return
    candidates = db.list_candidates(section, limit=30)
    if not candidates:
        await callback.message.answer("Bu bo‘limda nomzod topilmadi.", reply_markup=back_admin_keyboard())
        return
    await callback.message.answer("Nomzodni tanlang:", reply_markup=candidates_list_keyboard(candidates, section))


@router.callback_query(F.data == "clk:sync")
async def clockster_sync_now(callback: CallbackQuery) -> None:
    await callback.answer()
    if not admin_only(callback.from_user.id):
        return
    await callback.message.answer("Clockster sinxronizatsiya boshlandi...")
    result = await sync_all_clockster_attendance()
    msg = (
        "🔄 <b>Clockster sync yakunlandi</b>\n"
        f"Muvaffaqiyatli: <b>{h(result.get('synced', 0))}</b>\n"
        f"Xatolik: <b>{h(result.get('failed', 0))}</b>\n"
        f"Xabar: {h(result.get('message', ''))}"
    )
    errors = result.get("messages") or []
    if errors:
        msg += "\n\n" + "\n".join(h(x) for x in errors[:5])
    await callback.message.answer(msg, reply_markup=clockster_keyboard())


@router.callback_query(F.data == "clk:list")
async def clockster_employee_list(callback: CallbackQuery) -> None:
    await callback.answer()
    if not admin_only(callback.from_user.id):
        return
    employees = db.clockster_dashboard(limit=30)
    if not employees:
        await callback.message.answer("Xodimlar topilmadi.", reply_markup=clockster_keyboard())
        return
    await callback.message.answer("Qaysi xodimning kelib-ketishini ko‘rasiz?", reply_markup=clockster_employee_keyboard(employees))


@router.callback_query(F.data.startswith("clk:e:"))
async def clockster_employee_card(callback: CallbackQuery) -> None:
    await callback.answer()
    if not admin_only(callback.from_user.id):
        return
    employee_id = int((callback.data or "clk:e:0").split(":")[2])
    employee = db.get_employee(employee_id)
    if not employee:
        await callback.message.answer("Xodim topilmadi.", reply_markup=clockster_keyboard())
        return
    await sync_employee_attendance(employee_id)
    employee = db.get_employee(employee_id) or employee
    records = db.clockster_attendance_for_employee(employee_id, limit=15)
    lines = [
        f"🕒 <b>{h(employee.get('full_name'))}</b>",
        f"Bo‘lim: {h(employee.get('department'))}",
        f"Clockster ID: {h(employee.get('clockster_employee_id') or 'bog‘lanmagan')}",
        f"Oxirgi sync: {h(employee.get('clockster_last_sync_at') or '-')}",
    ]
    if not records:
        lines.append("\nHozircha kelib-ketish yozuvlari topilmadi.")
    else:
        lines.append("\n<b>Oxirgi yozuvlar:</b>")
        for r in records:
            lines.append(
                f"• {h(r.get('record_date'))}: keldi {h(r.get('check_in') or '-')} | ketdi {h(r.get('check_out') or '-')} | {h(r.get('status') or '-')}"
            )
    await callback.message.answer("\n".join(lines), reply_markup=clockster_keyboard())


@router.callback_query(F.data == "clk:logs")
async def clockster_logs(callback: CallbackQuery) -> None:
    await callback.answer()
    if not admin_only(callback.from_user.id):
        return
    logs = db.clockster_recent_sync_logs(limit=15)
    if not logs:
        await callback.message.answer("Clockster sync loglari hali yo‘q.", reply_markup=clockster_keyboard())
        return
    lines = ["🧾 <b>Oxirgi Clockster sync loglar</b>"]
    for row in logs:
        lines.append(f"#{row['id']} emp:{h(row.get('employee_id'))} | {h(row.get('status'))} | {h(row.get('message'))} | {h(row.get('created_at'))}")
    await callback.message.answer("\n".join(lines), reply_markup=clockster_keyboard())


@router.callback_query(F.data.startswith("adm_c:"))
async def candidate_card(callback: CallbackQuery) -> None:
    await callback.answer()
    if not admin_only(callback.from_user.id):
        return
    cid = int((callback.data or "adm_c:0").split(":")[1])
    c = db.get_candidate(cid)
    if not c:
        await callback.message.answer("Nomzod topilmadi.")
        return
    duplicate = f"\n⚠️ Oldingi ariza ID: #{c.get('duplicate_of_candidate_id')}" if c.get("duplicate_of_candidate_id") else ""
    text = (
        f"👤 <b>Nomzod #{cid}</b>{duplicate}\n"
        f"F.I.SH.: <b>{h(c.get('full_name'))}</b>\n"
        f"Lavozim: {h(c.get('position'))}\n"
        f"Telefon: {h(c.get('phone'))}\n"
        f"Hudud: {h(c.get('region'))}, {h(c.get('district'))}\n"
        f"AI: <b>{h(c.get('ai_score'))}</b> | {h(c.get('ai_grade'))}\n"
        f"Status: <b>{h(c.get('status'))}</b>\n"
        f"Admin izoh: {h(c.get('admin_note'))}"
    )
    await callback.message.answer(text, reply_markup=candidate_card_keyboard(cid))


@router.callback_query(F.data.startswith("adm_pdf:"))
async def candidate_pdf(callback: CallbackQuery) -> None:
    await callback.answer()
    if not admin_only(callback.from_user.id):
        return
    cid = int((callback.data or "adm_pdf:0").split(":")[1])
    path = generate_candidate_pdf(cid)
    await callback.message.answer_document(FSInputFile(path), caption=f"PDF anketa #{cid}")


@router.callback_query(F.data.startswith("adm_ai:"))
async def candidate_ai(callback: CallbackQuery) -> None:
    await callback.answer()
    if not admin_only(callback.from_user.id):
        return
    cid = int((callback.data or "adm_ai:0").split(":")[1])
    c = db.get_candidate(cid)
    ai = db.get_latest_ai_interview_for_candidate(cid)
    if not c:
        return
    text = (
        f"🤖 <b>AI xulosa #{cid}</b>\n"
        f"Score: <b>{h(c.get('ai_score'))}</b>\n"
        f"Grade: {h(c.get('ai_grade'))}\n"
        f"Tavsiya: {h(c.get('ai_admin_recommendation'))}\n"
        f"Xulosa: {h(c.get('ai_summary'))}\n"
        f"Sabablar: {h(c.get('ai_reasoning'))}"
    )
    await callback.message.answer(text, reply_markup=back_admin_keyboard())


@router.callback_query(F.data.startswith("adm_inv:"))
async def invite_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not admin_only(callback.from_user.id):
        return
    cid = int((callback.data or "adm_inv:0").split(":")[1])
    await state.set_state(AdminFlow.interview_info)
    await state.update_data(candidate_id=cid)
    await callback.message.answer("Intervyu vaqtini shu formatda yuboring:\n<code>2026-05-20 15:00 | Chilonzor filiali</code>")


@router.message(AdminFlow.interview_info)
async def invite_save(message: Message, state: FSMContext) -> None:
    if not admin_only(message.from_user.id):
        return
    data = await state.get_data()
    cid = int(data["candidate_id"])
    c = db.get_candidate(cid)
    if not c:
        await message.answer("Nomzod topilmadi.")
        return
    try:
        dt, location = parse_interview_input(message.text or "")
    except Exception:
        await message.answer("Format noto‘g‘ri. Masalan: 2026-05-20 15:00 | Chilonzor filiali")
        return
    followup = dt + timedelta(hours=24)
    interview_id = db.schedule_interview(cid, dt.strftime("%Y-%m-%d %H:%M:%S"), location, message.from_user.id, followup.strftime("%Y-%m-%d %H:%M:%S"))
    schedule_followup(message.bot, interview_id, followup)
    await message.bot.send_message(
        int(c["telegram_id"]),
        f"📅 Siz intervyuga chaqirildingiz.\n\nSana-vaqt: <b>{dt.strftime('%Y-%m-%d %H:%M')}</b>\nManzil: <b>{h(location)}</b>\n\nIltimos, vaqtida kelishingizni va kerakli hujjatlaringizni tayyorlab qo‘yishingizni so‘raymiz.",
    )
    await message.answer("Intervyu belgilandi va nomzodga yuborildi.", reply_markup=admin_main_keyboard())
    await state.clear()


@router.callback_query(F.data.startswith("adm_acc:"))
async def accept_choose_department(callback: CallbackQuery) -> None:
    await callback.answer()
    if not admin_only(callback.from_user.id):
        return
    cid = int((callback.data or "adm_acc:0").split(":")[1])
    await callback.message.answer("Qabul qilingan bo‘limni tanlang:", reply_markup=admin_department_keyboard(cid, db.list_vacancies(status="active")))


@router.callback_query(F.data.startswith("adm_dept:"))
async def accept_department(callback: CallbackQuery) -> None:
    await callback.answer()
    if not admin_only(callback.from_user.id):
        return
    _, cid, vacancy_id = (callback.data or "adm_dept:0:0").split(":")
    vacancy = db.get_vacancy(int(vacancy_id))
    if not vacancy:
        await callback.message.answer("Vakansiya topilmadi.")
        return
    department = vacancy.get("name_uz") or ""
    employee_id = db.create_employee(int(cid), department)
    ensure_lessons(employee_id)
    c = db.get_candidate(int(cid))
    await callback.message.answer(
        f"Nomzod qabul qilindi. Employee ID: #{employee_id}\n"
        "Clockster nazorati hozir ulanmaydi — u 7 kunlik stajirovka va yakuniy 30 talik test tugagandan keyin avtomatik boshlanadi.",
        reply_markup=admin_main_keyboard(),
    )
    if c:
        await callback.message.bot.send_message(int(c["telegram_id"]), f"Tabriklaymiz! Siz <b>{h(department)}</b> bo‘limiga qabul qilindingiz. 7 kunlik stajirovka boshlanadi.")
        await send_current_lesson(callback.message.bot, int(c["telegram_id"]), employee_id)


@router.callback_query(F.data.startswith("adm_rej:"))
async def reject_candidate(callback: CallbackQuery) -> None:
    await callback.answer()
    if not admin_only(callback.from_user.id):
        return
    cid = int((callback.data or "adm_rej:0").split(":")[1])
    db.update_candidate(cid, status="rejected")
    c = db.get_candidate(cid)
    if c:
        await callback.message.bot.send_message(int(c["telegram_id"]), "Arizangiz ko‘rib chiqildi. Afsuski, hozircha tanlovdan o‘tmadingiz. Kelgusi imkoniyatlarda omad tilaymiz.")
    await callback.message.answer("Nomzod rad etildi.", reply_markup=admin_main_keyboard())


@router.callback_query(F.data.startswith("adm_res:"))
async def reserve_candidate(callback: CallbackQuery) -> None:
    await callback.answer()
    if not admin_only(callback.from_user.id):
        return
    cid = int((callback.data or "adm_res:0").split(":")[1])
    db.update_candidate(cid, status="reserve")
    await callback.message.answer("Nomzod zaxiraga olindi.", reply_markup=admin_main_keyboard())


@router.callback_query(F.data.startswith("adm_note:"))
async def note_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not admin_only(callback.from_user.id):
        return
    cid = int((callback.data or "adm_note:0").split(":")[1])
    await state.set_state(AdminFlow.note)
    await state.update_data(candidate_id=cid)
    await callback.message.answer("Admin izohini yozing:")


@router.message(AdminFlow.note)
async def note_save(message: Message, state: FSMContext) -> None:
    if not admin_only(message.from_user.id):
        return
    data = await state.get_data()
    cid = int(data["candidate_id"])
    db.update_candidate(cid, admin_note=message.text or "")
    await message.answer("Izoh saqlandi.", reply_markup=admin_main_keyboard())
    await state.clear()
