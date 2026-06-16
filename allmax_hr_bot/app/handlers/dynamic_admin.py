from __future__ import annotations

import json
import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database import db
from app.keyboards.dynamic_admin_keyboards import (
    after_vacancy_keyboard,
    batch_activate_keyboard,
    confirm_regulation_keyboard,
    dynamic_home_keyboard,
    link_regulation_keyboard,
    material_actions_keyboard,
    multi_vacancy_select_keyboard,
    regulations_keyboard,
    regulations_manage_keyboard,
    regulation_type_keyboard,
    schedule_choices_keyboard,
    vacancy_edit_fields_keyboard,
    vacancy_manage_keyboard,
    vacancies_keyboard,
    vacancy_status_keyboard,
    version_keyboard,
    visibility_keyboard,
    yes_no_keyboard,
)
from app.services.dynamic_service import (
    REGULATION_TYPES,
    compare_regulations,
    extract_text,
    safe_filename,
    summarize_text,
    catalog_warnings,
)
from app.services.material_service import generate_material_drafts, material_summary
from app.states import DynamicAdminFlow
from app.utils.validators import h, chunk_text
from app.config import settings

router = Router()
logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return db.is_admin(user_id)


async def deny(callback: CallbackQuery) -> bool:
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return True
    await callback.answer()
    return False


def _vacancy_card(v: dict) -> str:
    return (
        f"📌 <b>{h(v.get('name_uz'))}</b> / {h(v.get('name_ru'))}\n"
        f"Status: <b>{h(v.get('status'))}</b>\n"
        f"Tavsif: {h(v.get('description_uz'))}\n"
        f"Ish grafigi: {h(v.get('work_schedule'))}\n"
        f"Intervyu: {h(v.get('interview_question_count'))} savol | "
        f"Stajirovka: {h(v.get('internship_days'))} kun / {h(v.get('lesson_count'))} dars | "
        f"Yakuniy test: {h(v.get('final_test_count'))}"
    )


@router.callback_query(F.data == "dyn:home")
async def dynamic_home(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback):
        return
    await state.clear()
    warnings = catalog_warnings()
    text = "⚙️ <b>Dinamik boshqaruv paneli</b>\nVakansiya, reglament va AI materiallarni shu yerdan boshqaring."
    if warnings:
        text += "\n\n⚠️ <b>Ogohlantirishlar</b>\n" + "\n".join(f"• {h(x)}" for x in warnings)
    await callback.message.answer(text, reply_markup=dynamic_home_keyboard())


@router.callback_query(F.data == "dyn:vac")
async def vacancy_home(callback: CallbackQuery) -> None:
    if await deny(callback):
        return
    await callback.message.answer("📋 <b>Vakansiyalarni boshqarish</b>", reply_markup=vacancy_manage_keyboard())


@router.callback_query(F.data == "dyn:vlist")
async def vacancy_list(callback: CallbackQuery) -> None:
    if await deny(callback):
        return
    items = db.list_vacancies()
    if not items:
        await callback.message.answer("Vakansiyalar mavjud emas.", reply_markup=vacancy_manage_keyboard())
        return
    text = "📋 <b>Vakansiyalar</b>\n\n" + "\n".join(f"• {h(v['name_uz'])} — <b>{h(v['status'])}</b>" for v in items)
    await callback.message.answer(text, reply_markup=vacancy_manage_keyboard())


@router.callback_query(F.data == "dyn:vnew")
async def vacancy_new_start(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback):
        return
    await state.clear()
    await state.set_state(DynamicAdminFlow.vacancy_name_uz)
    await state.update_data(new_vacancy={})
    await callback.message.answer("1/7. Yangi vakansiyaning o‘zbekcha nomini yozing.\nMasalan: <code>SMM Manager</code>")


@router.message(DynamicAdminFlow.vacancy_name_uz)
async def vacancy_name_uz(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    value = (message.text or "").strip()
    if len(value) < 2:
        await message.answer("Vakansiya nomini to‘liqroq yozing.")
        return
    await state.update_data(new_vacancy={"name_uz": value})
    await state.set_state(DynamicAdminFlow.vacancy_name_ru)
    await message.answer("2/7. Vakansiyaning ruscha nomini yozing.")


@router.message(DynamicAdminFlow.vacancy_name_ru)
async def vacancy_name_ru(message: Message, state: FSMContext) -> None:
    data = await state.get_data(); item = dict(data.get("new_vacancy") or {})
    item["name_ru"] = (message.text or "").strip()
    await state.update_data(new_vacancy=item)
    await state.set_state(DynamicAdminFlow.vacancy_description)
    await message.answer("3/7. Qisqa tavsifini yozing.")


@router.message(DynamicAdminFlow.vacancy_description)
async def vacancy_description(message: Message, state: FSMContext) -> None:
    data = await state.get_data(); item = dict(data.get("new_vacancy") or {})
    item["description_uz"] = (message.text or "").strip()
    await state.update_data(new_vacancy=item)
    await state.set_state(DynamicAdminFlow.vacancy_responsibilities)
    await message.answer("4/7. Asosiy vazifalarni punktlar bilan yozing.")


@router.message(DynamicAdminFlow.vacancy_responsibilities)
async def vacancy_responsibilities(message: Message, state: FSMContext) -> None:
    data = await state.get_data(); item = dict(data.get("new_vacancy") or {})
    item["responsibilities"] = (message.text or "").strip()
    await state.update_data(new_vacancy=item)
    await state.set_state(DynamicAdminFlow.vacancy_requirements)
    await message.answer("5/7. Asosiy talablarni yozing.")


@router.message(DynamicAdminFlow.vacancy_requirements)
async def vacancy_requirements(message: Message, state: FSMContext) -> None:
    data = await state.get_data(); item = dict(data.get("new_vacancy") or {})
    item["requirements"] = (message.text or "").strip()
    await state.update_data(new_vacancy=item)
    await message.answer("6/7. Ish grafigini tanlang:", reply_markup=schedule_choices_keyboard())


@router.callback_query(F.data.startswith("dyn:vsch:"))
async def vacancy_schedule(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback):
        return
    value = (callback.data or "").split(":", 2)[2]
    if value == "custom":
        await state.set_state(DynamicAdminFlow.vacancy_schedule_custom)
        await callback.message.answer("Ish grafigini matn ko‘rinishida yozing.")
        return
    data = await state.get_data(); item = dict(data.get("new_vacancy") or {})
    item["work_schedule"] = value
    await state.update_data(new_vacancy=item)
    await callback.message.answer("7/7. Vakansiya userlarga ko‘rinsinmi?", reply_markup=visibility_keyboard())


@router.message(DynamicAdminFlow.vacancy_schedule_custom)
async def vacancy_schedule_custom(message: Message, state: FSMContext) -> None:
    data = await state.get_data(); item = dict(data.get("new_vacancy") or {})
    item["work_schedule"] = (message.text or "").strip()
    await state.update_data(new_vacancy=item)
    await message.answer("7/7. Vakansiya userlarga ko‘rinsinmi?", reply_markup=visibility_keyboard())


@router.callback_query(F.data.startswith("dyn:vvis:"))
async def vacancy_visibility(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback):
        return
    status = (callback.data or "").split(":")[2]
    data = await state.get_data(); item = dict(data.get("new_vacancy") or {})
    item["status"] = status
    vid = db.create_vacancy(item, callback.from_user.id)
    await state.clear()
    vacancy = db.get_vacancy(vid) or item
    await callback.message.answer(f"✅ Vakansiya saqlandi.\n\n{_vacancy_card(vacancy)}\n\nReglament biriktirilsinmi?", reply_markup=after_vacancy_keyboard(vid))


@router.callback_query(F.data == "dyn:vedit")
async def vacancy_edit_select(callback: CallbackQuery) -> None:
    if await deny(callback):
        return
    await callback.message.answer("Tahrirlanadigan vakansiyani tanlang:", reply_markup=vacancies_keyboard(db.list_vacancies(include_archived=False), "dyn:veditpick"))


@router.callback_query(F.data.startswith("dyn:veditpick:"))
async def vacancy_edit_fields(callback: CallbackQuery) -> None:
    if await deny(callback):
        return
    vid = int((callback.data or "").split(":")[2]); v = db.get_vacancy(vid)
    if not v:
        return
    await callback.message.answer(_vacancy_card(v) + "\n\nQaysi maydonni o‘zgartirasiz?", reply_markup=vacancy_edit_fields_keyboard(vid))


@router.callback_query(F.data.startswith("dyn:vef:"))
async def vacancy_edit_value_start(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback):
        return
    _, _, vid, field = (callback.data or "").split(":", 3)
    await state.set_state(DynamicAdminFlow.vacancy_edit_value)
    await state.update_data(edit_vacancy_id=int(vid), edit_vacancy_field=field)
    await callback.message.answer(f"Yangi qiymatni yuboring. Maydon: <b>{h(field)}</b>")


@router.message(DynamicAdminFlow.vacancy_edit_value)
async def vacancy_edit_value_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data(); vid = int(data["edit_vacancy_id"]); field = data["edit_vacancy_field"]
    value: object = (message.text or "").strip()
    if field in {"interview_question_count", "internship_days", "lesson_count", "final_test_count"}:
        try:
            value = int(str(value)); assert int(value) > 0
        except Exception:
            await message.answer("Bu maydon uchun musbat son yozing.")
            return
    db.update_vacancy(vid, message.from_user.id, **{field: value})
    await state.clear()
    await message.answer("✅ Vakansiya yangilandi.", reply_markup=vacancy_edit_fields_keyboard(vid))


@router.callback_query(F.data.startswith("dyn:vstatus:"))
async def status_choose_vacancy(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback):
        return
    target = (callback.data or "").split(":")[2]
    await state.update_data(target_vacancy_status=target)
    await callback.message.answer("Vakansiyani tanlang:", reply_markup=vacancies_keyboard(db.list_vacancies(), "dyn:vstatuspick"))


@router.callback_query(F.data.startswith("dyn:vstatuspick:"))
async def status_apply_pick(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback):
        return
    vid = int((callback.data or "").split(":")[2])
    status = (await state.get_data()).get("target_vacancy_status", "hidden")
    if status == "archived":
        await callback.message.answer("Diqqat! Vakansiyani arxivlasangiz, yangi ariza qabul qilinmaydi. Tasdiqlaysizmi?", reply_markup=yes_no_keyboard(f"dyn:vset:{vid}:archived", "dyn:vac"))
    else:
        db.update_vacancy(vid, callback.from_user.id, status=status)
        await callback.message.answer(f"✅ Status o‘zgardi: <b>{h(status)}</b>", reply_markup=vacancy_manage_keyboard())


@router.callback_query(F.data.startswith("dyn:vshowstatus:"))
async def show_status(callback: CallbackQuery) -> None:
    if await deny(callback):
        return
    vid = int((callback.data or "").split(":")[2])
    await callback.message.answer("Yangi statusni tanlang:", reply_markup=vacancy_status_keyboard(vid))


@router.callback_query(F.data.startswith("dyn:vconfirmarc:"))
async def confirm_archive_vacancy(callback: CallbackQuery) -> None:
    if await deny(callback):
        return
    vid = int((callback.data or "").split(":")[2])
    await callback.message.answer("Diqqat! Vakansiyani arxivlashni tasdiqlaysizmi?", reply_markup=yes_no_keyboard(f"dyn:vset:{vid}:archived", "dyn:vac"))


@router.callback_query(F.data.startswith("dyn:vset:"))
async def set_status(callback: CallbackQuery) -> None:
    if await deny(callback):
        return
    _, _, vid, status = (callback.data or "").split(":")
    db.update_vacancy(int(vid), callback.from_user.id, status=status)
    await callback.message.answer(f"✅ Vakansiya statusi: <b>{h(status)}</b>", reply_markup=vacancy_manage_keyboard())


@router.callback_query(F.data == "dyn:reg")
async def regulation_home(callback: CallbackQuery) -> None:
    if await deny(callback):
        return
    await callback.message.answer("📚 <b>Reglamentlarni boshqarish</b>", reply_markup=regulations_manage_keyboard())


@router.callback_query(F.data == "dyn:rlist")
async def regulation_list(callback: CallbackQuery) -> None:
    if await deny(callback):
        return
    regs = db.list_regulations()
    lines = ["📚 <b>Reglamentlar</b>"]
    for reg in regs:
        version = f"v{reg.get('current_version_number')}" if reg.get("current_version_number") else "versiya yo‘q"
        lines.append(f"• {h(reg.get('title'))} — {h(version)} / {h(reg.get('status'))}")
    await callback.message.answer("\n".join(lines) if len(lines) > 1 else "Reglament topilmadi.", reply_markup=regulations_manage_keyboard())


@router.callback_query(F.data == "dyn:rnew")
async def regulation_new(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback):
        return
    await state.clear(); await state.set_state(DynamicAdminFlow.regulation_title); await state.update_data(reg_mode="new", selected_vacancies=[])
    await callback.message.answer("Reglament nomini yozing. Masalan: <code>SMM Manager reglamenti</code>")


@router.message(DynamicAdminFlow.regulation_title)
async def regulation_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if len(title) < 3:
        await message.answer("Reglament nomini to‘liqroq yozing.")
        return
    await state.update_data(reg_title=title, selected_vacancies=[])
    await message.answer("Reglament tegishli bo‘lgan bir yoki bir nechta vakansiyani belgilang:", reply_markup=multi_vacancy_select_keyboard(db.list_vacancies(include_archived=False), set()))


@router.callback_query(F.data.startswith("dyn:rvsel:"))
async def regulation_vacancy_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback):
        return
    vid = int((callback.data or "").split(":")[2])
    data = await state.get_data(); selected = set(data.get("selected_vacancies") or [])
    if vid in selected: selected.remove(vid)
    else: selected.add(vid)
    await state.update_data(selected_vacancies=list(selected))
    await callback.message.edit_reply_markup(reply_markup=multi_vacancy_select_keyboard(db.list_vacancies(include_archived=False), selected))


@router.callback_query(F.data == "dyn:rfile")
async def regulation_choose_type_or_file(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback):
        return
    data = await state.get_data()
    if data.get("reg_mode") == "update" and data.get("regulation_id"):
        await state.set_state(DynamicAdminFlow.regulation_update_file)
        await callback.message.answer("Yangi versiya faylini yuboring: .docx, .pdf yoki .txt")
        return
    if not data.get("selected_vacancies"):
        await callback.message.answer("Kamida bitta vakansiyani tanlang.")
        return
    await callback.message.answer("Reglament turini tanlang:", reply_markup=regulation_type_keyboard())


@router.callback_query(F.data.startswith("dyn:rtype:"))
async def regulation_type_selected(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback):
        return
    idx = int((callback.data or "").split(":")[2])
    await state.update_data(regulation_type=REGULATION_TYPES[idx])
    await state.set_state(DynamicAdminFlow.regulation_upload_file)
    await callback.message.answer("Reglament faylini yuboring: <b>.docx</b>, <b>.pdf</b> yoki <b>.txt</b>.")


async def _receive_regulation_document(message: Message, state: FSMContext, update_existing: bool) -> None:
    if not is_admin(message.from_user.id):
        return
    if not message.document:
        await message.answer("Iltimos, faylni document ko‘rinishida yuboring.")
        return
    filename = message.document.file_name or "reglament.txt"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".docx", ".pdf", ".txt"}:
        await message.answer("Faqat .docx, .pdf yoki .txt format qabul qilinadi.")
        return
    uploads = settings.regulations_dir / "uploads"; uploads.mkdir(parents=True, exist_ok=True)
    stored = uploads / safe_filename(filename)
    await message.bot.download(message.document, destination=stored)
    text, warning = extract_text(stored)
    if warning and len(text) < 40:
        stored.unlink(missing_ok=True)
        await message.answer(h(warning))
        return
    data = await state.get_data()
    if update_existing:
        rid = int(data["regulation_id"])
        old = db.get_regulation(rid) or {}
        oldver = db.get_regulation_version(int(old.get("current_version_id") or 0)) if old.get("current_version_id") else None
        change = compare_regulations((oldver or {}).get("extracted_text") or "", text)
        title = old.get("title") or filename
        rtype = old.get("regulation_type") or "Qo‘shimcha qoida"
    else:
        title = data.get("reg_title") or Path(filename).stem
        rtype = data.get("regulation_type") or "Qo‘shimcha qoida"
        rid = db.create_regulation(title, rtype, message.from_user.id)
        change = "Yangi reglament — v1."
    summary = summarize_text(text)
    version_id = db.add_regulation_version(rid, filename, str(stored.relative_to(settings.regulations_dir.parent)), suffix, text, summary, change, message.from_user.id, active=False)
    await state.update_data(pending_regulation_id=rid, pending_version_id=version_id)
    version = db.get_regulation_version(version_id) or {}
    body = (
        f"📚 <b>{h(title)}</b>\n"
        f"Turi: {h(rtype)}\nVersiya: <b>v{h(version.get('version_number'))}</b>\nFayl turi: {h(suffix)}\n\n"
        f"<b>O‘qilgan qisqa mazmun:</b>\n{h(summary)}\n\n"
        f"<b>O‘zgarish xulosasi:</b>\n{h(change)}"
    )
    if warning:
        body += f"\n\n⚠️ {h(warning)}"
    await message.answer(body, reply_markup=confirm_regulation_keyboard())


@router.message(DynamicAdminFlow.regulation_upload_file)
async def regulation_file_new(message: Message, state: FSMContext) -> None:
    await _receive_regulation_document(message, state, False)


@router.message(DynamicAdminFlow.regulation_update_file)
async def regulation_file_update(message: Message, state: FSMContext) -> None:
    await _receive_regulation_document(message, state, True)


@router.callback_query(F.data == "dyn:ractivate")
async def activate_uploaded_regulation(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback):
        return
    data = await state.get_data(); version_id = int(data.get("pending_version_id") or 0)
    if not version_id:
        await callback.message.answer("Tasdiqlanadigan versiya topilmadi.")
        return
    db.activate_regulation_version(version_id, callback.from_user.id)
    selected = data.get("selected_vacancies") or []
    regulation_id = int(data.get("pending_regulation_id"))
    for vid in selected:
        db.link_vacancy_regulation(int(vid), regulation_id, callback.from_user.id, version_id)
    if not selected:
        selected = [int(v["id"]) for v in db.vacancies_for_regulation(regulation_id)]
    await callback.message.answer("✅ Reglament versiyasi faollashtirildi. Yangi nomzodlar va yangi stajirovkalar ushbu faol versiya asosida ishlaydi.")
    if selected:
        for vid in selected:
            vacancy = db.get_vacancy(int(vid)) or {}
            await callback.message.answer(f"🧠 <b>{h(vacancy.get('name_uz'))}</b> uchun AI savollar, darslar va testlarni yangi reglament asosida qayta yaratilsinmi?", reply_markup=material_actions_keyboard(int(vid)))
    else:
        await callback.message.answer("Reglamentni kerakli vakansiyaga bog‘lash bo‘limidan biriktiring.", reply_markup=dynamic_home_keyboard())
    await state.clear()


@router.callback_query(F.data == "dyn:rupd")
async def regulation_update_select(callback: CallbackQuery) -> None:
    if await deny(callback): return
    await callback.message.answer("Yangilanadigan reglamentni tanlang:", reply_markup=regulations_keyboard(db.list_regulations(include_archived=False), "dyn:rupdpick"))


@router.callback_query(F.data.startswith("dyn:rupdpick:"))
async def regulation_update_start(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback): return
    rid = int((callback.data or "").split(":")[2]); reg = db.get_regulation(rid)
    await state.clear(); await state.update_data(reg_mode="update", regulation_id=rid, pending_regulation_id=rid, selected_vacancies=[]); await state.set_state(DynamicAdminFlow.regulation_update_file)
    await callback.message.answer(f"Hozirgi reglament: <b>{h((reg or {}).get('title'))}</b>. Yangi .docx, .pdf yoki .txt faylni yuboring.")


@router.callback_query(F.data.in_({"dyn:versions", "dyn:rrollback"}))
async def versions_select_reg(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback): return
    rollback = callback.data == "dyn:rrollback"
    await state.update_data(version_mode="rollback" if rollback else "view")
    await callback.message.answer("Reglamentni tanlang:", reply_markup=regulations_keyboard(db.list_regulations(), "dyn:verreg"))


@router.callback_query(F.data.startswith("dyn:verreg:"))
async def versions_show(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback): return
    rid = int((callback.data or "").split(":")[2]); mode=(await state.get_data()).get("version_mode","view")
    prefix = "dyn:rollbackver" if mode == "rollback" else "dyn:viewver"
    await callback.message.answer("Versiyalar:", reply_markup=version_keyboard(db.regulation_versions(rid), prefix))


@router.callback_query(F.data.startswith("dyn:viewver:"))
async def version_detail(callback: CallbackQuery) -> None:
    if await deny(callback): return
    vid=int((callback.data or "").split(":")[2]); v=db.get_regulation_version(vid) or {}
    await callback.message.answer(f"📦 <b>{h(v.get('title'))} — v{h(v.get('version_number'))}</b>\nFaol: {h('Ha' if v.get('is_active') else 'Yo‘q')}\nYuklangan sana: {h(v.get('uploaded_at'))}\n\n{h(v.get('ai_summary'))}")


@router.callback_query(F.data.startswith("dyn:rollbackver:"))
async def rollback_confirm(callback: CallbackQuery) -> None:
    if await deny(callback): return
    vid=int((callback.data or "").split(":")[2]); v=db.get_regulation_version(vid) or {}
    await callback.message.answer(f"Diqqat! <b>{h(v.get('title'))} — v{h(v.get('version_number'))}</b> versiyasini yana faol qilmoqchimisiz? Bu yangi nomzodlar va yangi stajirovkalarga ta’sir qiladi.", reply_markup=yes_no_keyboard(f"dyn:rollbackok:{vid}", "dyn:reg"))


@router.callback_query(F.data.startswith("dyn:rollbackok:"))
async def rollback_apply(callback: CallbackQuery) -> None:
    if await deny(callback): return
    vid=int((callback.data or "").split(":")[2]); db.activate_regulation_version(vid, callback.from_user.id)
    await callback.message.answer("✅ Tanlangan eski versiya qayta faollashtirildi.", reply_markup=regulations_manage_keyboard())


@router.callback_query(F.data == "dyn:rarchive")
async def regulation_archive_pick(callback: CallbackQuery) -> None:
    if await deny(callback): return
    await callback.message.answer("Arxivlanadigan reglamentni tanlang:", reply_markup=regulations_keyboard(db.list_regulations(include_archived=False), "dyn:rarchivepick"))


@router.callback_query(F.data.startswith("dyn:rarchivepick:"))
async def regulation_archive_confirm(callback: CallbackQuery) -> None:
    if await deny(callback): return
    rid=int((callback.data or "").split(":")[2]); reg=db.get_regulation(rid) or {}
    await callback.message.answer(f"<b>{h(reg.get('title'))}</b> reglamentini arxivlashni tasdiqlaysizmi?", reply_markup=yes_no_keyboard(f"dyn:rarchiveok:{rid}", "dyn:reg"))


@router.callback_query(F.data.startswith("dyn:rarchiveok:"))
async def regulation_archive_apply(callback: CallbackQuery) -> None:
    if await deny(callback): return
    rid=int((callback.data or "").split(":")[2]); db.archive_regulation(rid, callback.from_user.id)
    await callback.message.answer("✅ Reglament arxivlandi.", reply_markup=regulations_manage_keyboard())


@router.callback_query(F.data == "dyn:link")
async def link_pick_vacancy(callback: CallbackQuery) -> None:
    if await deny(callback): return
    await callback.message.answer("Reglament bog‘lanadigan vakansiyani tanlang:", reply_markup=vacancies_keyboard(db.list_vacancies(include_archived=False), "dyn:linksel"))


@router.callback_query(F.data.startswith("dyn:linksel:"))
async def link_show_regulations(callback: CallbackQuery) -> None:
    if await deny(callback): return
    vid=int((callback.data or "").split(":")[2])
    linked={int(x['regulation_id']) for x in db.vacancy_regulation_links(vid)}
    active_regs = [r for r in db.list_regulations(include_archived=False) if r.get("status") == "active"]
    await callback.message.answer("Kerakli faol reglamentlarni belgilang va ishlatilish turini tanlang: intervyu, dars, test yoki hammasi uchun.", reply_markup=link_regulation_keyboard(active_regs, vid, linked))


@router.callback_query(F.data.startswith("dyn:togglelink:"))
async def link_toggle(callback: CallbackQuery) -> None:
    if await deny(callback): return
    _, _, vid, rid=(callback.data or "").split(":"); vid=int(vid); rid=int(rid)
    linked={int(x['regulation_id']) for x in db.vacancy_regulation_links(vid)}
    if rid in linked:
        db.unlink_vacancy_regulation(vid, rid, callback.from_user.id)
        new_linked={int(x['regulation_id']) for x in db.vacancy_regulation_links(vid)}
        active_regs = [r for r in db.list_regulations(include_archived=False) if r.get("status") == "active"]
        await callback.message.edit_reply_markup(reply_markup=link_regulation_keyboard(active_regs, vid, new_linked))
        return
    keys = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Hammasi uchun", callback_data=f"dyn:linkuse:{vid}:{rid}:all")],
        [InlineKeyboardButton(text="Intervyu uchun", callback_data=f"dyn:linkuse:{vid}:{rid}:int"), InlineKeyboardButton(text="Darslar uchun", callback_data=f"dyn:linkuse:{vid}:{rid}:les")],
        [InlineKeyboardButton(text="Testlar uchun", callback_data=f"dyn:linkuse:{vid}:{rid}:tst"), InlineKeyboardButton(text="Dars + Test", callback_data=f"dyn:linkuse:{vid}:{rid}:lest")],
    ])
    await callback.message.answer("Reglament qayerda ishlatilsin?", reply_markup=keys)


@router.callback_query(F.data.startswith("dyn:linkuse:"))
async def link_use_apply(callback: CallbackQuery) -> None:
    if await deny(callback): return
    _, _, vid, rid, mode=(callback.data or "").split(":"); vid=int(vid); rid=int(rid)
    use_int = mode in {"all", "int"}
    use_les = mode in {"all", "les", "lest"}
    use_tst = mode in {"all", "tst", "lest"}
    db.link_vacancy_regulation(vid, rid, callback.from_user.id, None, use_int, use_les, use_tst)
    linked={int(x['regulation_id']) for x in db.vacancy_regulation_links(vid)}
    active_regs = [r for r in db.list_regulations(include_archived=False) if r.get("status") == "active"]
    await callback.message.answer("✅ Reglament bog‘landi.", reply_markup=link_regulation_keyboard(active_regs, vid, linked))


@router.callback_query(F.data == "dyn:ai")
async def ai_pick_vacancy(callback: CallbackQuery) -> None:
    if await deny(callback): return
    await callback.message.answer("AI material yaratiladigan vakansiyani tanlang:", reply_markup=vacancies_keyboard(db.list_vacancies(include_archived=False), "dyn:ai_v"))


@router.callback_query(F.data.startswith("dyn:ai_v:"))
async def ai_material_actions(callback: CallbackQuery) -> None:
    if await deny(callback): return
    vid=int((callback.data or "").split(":")[2]); v=db.get_vacancy(vid) or {}
    await callback.message.answer(f"🧠 <b>{h(v.get('name_uz'))}</b> uchun nimani yaratamiz?", reply_markup=material_actions_keyboard(vid))


@router.callback_query(F.data.startswith("dyn:gen:"))
async def generate_materials(callback: CallbackQuery) -> None:
    if await deny(callback): return
    _, _, vid, mode=(callback.data or "").split(":"); vid=int(vid)
    kinds = {"interview", "lessons", "tests"} if mode == "all" else {mode}
    await callback.message.answer("⏳ AI materiallar yaratilmoqda. Bu amaliyot reglament hajmi va model tezligiga qarab vaqt olishi mumkin.")
    try:
        result = await generate_material_drafts(vid, kinds, callback.from_user.id)
    except Exception as exc:
        logger.exception("Material generation failed")
        await callback.message.answer(f"Material yaratishda xato: {h(exc)}")
        return
    text = (
        "✅ <b>Materiallar draft holatda tayyorlandi</b>\n"
        f"Intervyu savollari: {h(result.get('interview'))}\n"
        f"Darslar: {h(result.get('lessons'))}\n"
        f"Dars test savollari: {h(result.get('lesson_tests'))}\n"
        f"Yakuniy test savollari: {h(result.get('final_test'))}\n\n"
        "Userlarga yuborilishi uchun admin tasdiqlab faollashtirishi kerak."
    )
    await callback.message.answer(text, reply_markup=batch_activate_keyboard(vid, result["batch_key"]))


@router.callback_query(F.data.startswith("dyn:mactivate:"))
async def activate_material_batch(callback: CallbackQuery) -> None:
    if await deny(callback): return
    _, _, vid, batch=(callback.data or "").split(":", 3)
    db.activate_material_batch(int(vid), batch, callback.from_user.id)
    await callback.message.answer("✅ Materiallar faol qilindi. Endi yangi boshlanadigan intervyu va stajirovkalarda ishlatiladi.", reply_markup=dynamic_home_keyboard())


@router.callback_query(F.data == "dyn:mats")
async def material_pick_vacancy(callback: CallbackQuery) -> None:
    if await deny(callback): return
    await callback.message.answer("Materiallari ko‘riladigan vakansiyani tanlang:", reply_markup=vacancies_keyboard(db.list_vacancies(include_archived=False), "dyn:mat_v"))


@router.callback_query(F.data.startswith("dyn:mat_v:"))
async def material_view(callback: CallbackQuery) -> None:
    if await deny(callback): return
    vid=int((callback.data or "").split(":")[2]); v=db.get_vacancy(vid) or {}; summary=material_summary(vid)
    lines=[f"📊 <b>{h(v.get('name_uz'))} — materiallar</b>"]
    if not summary: lines.append("Material hali yaratilmagan.")
    for typ, statuses in summary.items(): lines.append(f"• {h(typ)}: " + ", ".join(f"{h(k)}={h(val)}" for k,val in statuses.items()))
    rows=[
        [InlineKeyboardButton(text="📘 Darslarni ko‘rish/tahrirlash", callback_data=f"dyn:matlist:{vid}")],
        [InlineKeyboardButton(text="📝 Test savollarini ko‘rish/tahrirlash", callback_data=f"dyn:qblist:{vid}")],
        [InlineKeyboardButton(text="🧠 Yangi material yaratish", callback_data=f"dyn:ai_v:{vid}")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="dyn:home")],
    ]
    await callback.message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data.startswith("dyn:matlist:"))
async def materials_list(callback: CallbackQuery) -> None:
    if await deny(callback): return
    vid=int((callback.data or "").split(":")[2]); items=db.list_training_materials(vid, None, "lesson", 30)
    rows=[]
    for item in items:
        rows.append([InlineKeyboardButton(text=f"{item['material_number']}. {item['title'][:42]} [{item['status']}]", callback_data=f"dyn:medit:{item['id']}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"dyn:mat_v:{vid}")])
    await callback.message.answer("Darsni tahrirlash uchun tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data.startswith("dyn:medit:"))
async def material_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback): return
    mid=int((callback.data or "").split(":")[2]); await state.set_state(DynamicAdminFlow.material_edit_value); await state.update_data(material_id=mid)
    await callback.message.answer("Yangi dars mazmunini yuboring. JSON formatida yuborsangiz barcha bo‘limlar saqlanadi; oddiy matn yuborsangiz content sifatida saqlanadi.")


@router.message(DynamicAdminFlow.material_edit_value)
async def material_edit_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id): return
    mid=int((await state.get_data())["material_id"]); db.update_training_material(mid, message.from_user.id, content=message.text or "")
    await state.clear(); await message.answer("✅ Dars materiali tahrirlandi.", reply_markup=dynamic_home_keyboard())


@router.callback_query(F.data.startswith("dyn:qblist:"))
async def question_list(callback: CallbackQuery) -> None:
    if await deny(callback): return
    vid=int((callback.data or "").split(":")[2]); items=db.list_question_bank_rows(vid, None, None, 40)
    rows=[]
    for q in items:
        label=f"{q['question_type']} {q['material_number']}/{q['question_number']} [{q['status']}]"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"dyn:qview:{q['id']}")])
    rows.append([InlineKeyboardButton(text="➕ Yangi yakuniy savol qo‘shish", callback_data=f"dyn:qadd:{vid}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"dyn:mat_v:{vid}")])
    await callback.message.answer("Savolni tanlang yoki yangi savol qo‘shing:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data.startswith("dyn:qview:"))
async def question_view(callback: CallbackQuery) -> None:
    if await deny(callback): return
    qid=int((callback.data or "").split(":")[2]); q=db.get_question_bank_row(qid) or {}
    opts=json.loads(q.get("options_json") or "{}")
    text=(f"📝 <b>Savol</b>: {h(q.get('question_text'))}\nA) {h(opts.get('A'))}\nB) {h(opts.get('B'))}\nC) {h(opts.get('C'))}\nD) {h(opts.get('D'))}\nTo‘g‘ri: <b>{h(q.get('correct_answer'))}</b>\nStatus: {h(q.get('status'))}")
    keys=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"dyn:qedit:{qid}"), InlineKeyboardButton(text="🗄 Arxivlash", callback_data=f"dyn:qarchive:{qid}")]])
    await callback.message.answer(text, reply_markup=keys)


@router.callback_query(F.data.startswith("dyn:qedit:"))
async def question_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback): return
    qid=int((callback.data or "").split(":")[2]); q=db.get_question_bank_row(qid) or {}
    await state.set_state(DynamicAdminFlow.question_edit_value); await state.update_data(question_id=qid, add_question=False)
    await callback.message.answer(f"Hozirgi savol: {h(q.get('question_text'))}\n\nYangi savolni quyidagi formatda yuboring:\n<code>Savol | A varianti | B varianti | C varianti | D varianti | A | Izoh</code>")


@router.callback_query(F.data.startswith("dyn:qadd:"))
async def question_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    if await deny(callback): return
    vid=int((callback.data or "").split(":")[2])
    await state.set_state(DynamicAdminFlow.question_edit_value); await state.update_data(add_question=True, question_vacancy_id=vid)
    await callback.message.answer("Yangi yakuniy test savolini quyidagi formatda yuboring:\n<code>Savol | A varianti | B varianti | C varianti | D varianti | A | Izoh</code>")


@router.callback_query(F.data.startswith("dyn:qarchive:"))
async def question_archive(callback: CallbackQuery) -> None:
    if await deny(callback): return
    qid=int((callback.data or "").split(":")[2]); db.update_question_bank_row(qid, callback.from_user.id, status="archived")
    await callback.message.answer("✅ Savol arxivlandi. Userlarga berilmaydi.", reply_markup=dynamic_home_keyboard())


@router.message(DynamicAdminFlow.question_edit_value)
async def question_edit_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id): return
    parts=[x.strip() for x in (message.text or "").split("|")]
    if len(parts) < 7 or parts[5].upper() not in {"A","B","C","D"}:
        await message.answer("Format noto‘g‘ri. 7 ta qism va to‘g‘ri javob A/B/C/D bo‘lishi kerak.")
        return
    data=await state.get_data(); options={"A":parts[1],"B":parts[2],"C":parts[3],"D":parts[4]}
    if data.get("add_question"):
        db.add_manual_question(int(data["question_vacancy_id"]), "final_test", 0, parts[0], options, parts[5].upper(), parts[6], message.from_user.id)
        result="✅ Yangi savol draft sifatida qo‘shildi."
    else:
        qid=int(data["question_id"]); db.update_question_bank_row(qid, message.from_user.id, question_text=parts[0], options_json=json.dumps(options, ensure_ascii=False), correct_answer=parts[5].upper(), explanation=parts[6])
        result="✅ Test savoli yangilandi."
    await state.clear(); await message.answer(result, reply_markup=dynamic_home_keyboard())


@router.callback_query(F.data == "dyn:logs")
async def change_logs(callback: CallbackQuery) -> None:
    if await deny(callback): return
    rows=db.recent_change_logs(30)
    lines=["📝 <b>O‘zgarishlar tarixi</b>"]
    for row in rows:
        lines.append(f"{h(row.get('created_at'))} | admin:{h(row.get('admin_id'))} | {h(row.get('action_type'))} | {h(row.get('entity_type'))} #{h(row.get('entity_id'))}")
    text="\n".join(lines) if rows else "O‘zgarishlar hali yo‘q."
    for part in chunk_text(text):
        await callback.message.answer(part, reply_markup=dynamic_home_keyboard() if part == chunk_text(text)[-1] else None)
