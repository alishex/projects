from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["DB_PATH"] = "data/smoke_test.db"
os.environ["OPENAI_API_KEY"] = ""
os.environ["ADMIN_IDS"] = "123456789"
os.environ["TIMEZONE"] = "Asia/Tashkent"

from app.database import db, loads
from app.services.dynamic_service import bootstrap_dynamic_catalog, extract_text, regulation_text_for_vacancy, brief_for_vacancy
from app.services.material_service import generate_material_drafts
from app.services.lesson_service import ensure_lessons
from app.utils.validators import h


def test() -> None:
    test_db = ROOT / "data" / "smoke_test.db"
    test_db.unlink(missing_ok=True)
    db.init()
    bootstrap_dynamic_catalog()
    assert len(db.list_vacancies(status="active")) >= 11, "Initial active vacancies not seeded"
    assert db.list_regulations(), "Initial regulations not imported"
    sample_docx = next(ROOT.glob("reglamentlar/*.docx"))
    docx_text, docx_warning = extract_text(sample_docx)
    assert len(docx_text) > 40, "DOCX text extraction failed"

    smm_id = db.create_vacancy({
        "name_uz": "SMM Manager <test>",
        "name_ru": "SMM менеджер",
        "description_uz": "Instagram <kontent> reja va auditoriya bilan ishlash.",
        "responsibilities": "Kontent-reja tuzish va mijoz xabarlariga javob berish.",
        "requirements": "Savodli matn va intizom.",
        "work_schedule": "To‘liq stavka",
        "status": "active",
    }, 123456789)
    assert any(v["id"] == smm_id for v in db.list_vacancies(status="active"))

    upload = ROOT / "reglamentlar" / "uploads" / "smoke_smm_v1.txt"
    upload.parent.mkdir(exist_ok=True, parents=True)
    upload.write_text("SMM Manager reglamenti. Har kuni kontent reja tuzadi. Mijozlarga hurmat bilan o‘z vaqtida javob beradi. Kun yakunida hisobot topshiradi.", encoding="utf-8")
    text, warning = extract_text(upload)
    assert text and not warning
    rid = db.create_regulation("SMM Manager reglamenti smoke", "Asosiy lavozim reglamenti", 123456789)
    v1 = db.add_regulation_version(rid, upload.name, str(upload), ".txt", text, "SMM reglament", "v1", 123456789, active=True)
    db.link_vacancy_regulation(smm_id, rid, 123456789, v1)
    snap_v1 = db.regulation_snapshot(smm_id)
    assert loads(snap_v1, [])[0]["version_id"] == v1

    v2_text = text + "\nHaftalik tahlil hisobotini tayyorlaydi."
    v2 = db.add_regulation_version(rid, "smoke_smm_v2.txt", str(upload), ".txt", v2_text, "v2", "yangi hisobot bandi", 123456789, active=False)
    db.activate_regulation_version(v2, 123456789)
    assert loads(db.regulation_snapshot(smm_id), [])[0]["version_id"] == v2
    db.activate_regulation_version(v1, 123456789)
    assert loads(db.regulation_snapshot(smm_id), [])[0]["version_id"] == v1, "Rollback failed"
    assert "kontent" in regulation_text_for_vacancy(smm_id, "interview", snap_v1).lower()

    result = asyncio.run(generate_material_drafts(smm_id, {"interview", "lessons", "tests"}, 123456789))
    assert result["interview"] == 10
    assert result["lessons"] == 20
    assert result["lesson_tests"] == 200
    assert result["final_test"] == 30
    db.activate_material_batch(smm_id, result["batch_key"], 123456789)
    assert len(db.list_training_materials(smm_id, "active", "lesson", 50)) == 20
    assert len(db.active_questions(smm_id, "lesson_test", 1, snap_v1)) == 10
    assert len(db.active_questions(smm_id, "final_test", 0, snap_v1)) == 30

    candidate_id = db.create_candidate({
        "telegram_id": 222,
        "full_name": "Test Xodim",
        "position": "SMM Manager <test>",
        "phone": "+998901234567",
        "vacancy_id": smm_id,
        "regulation_version_snapshot": snap_v1,
        "consent": 1,
    })
    employee_id = db.create_employee(candidate_id, "SMM Manager <test>")
    ensure_lessons(employee_id)
    employee = db.get_employee(employee_id)
    assert employee and employee["regulation_version_snapshot"] == snap_v1
    assert db.get_lesson(employee_id, 1), "Lesson instantiation failed"
    db.activate_regulation_version(v2, 123456789)
    assert db.get_employee(employee_id)["regulation_version_snapshot"] == snap_v1, "Ongoing internship snapshot changed unexpectedly"

    v = db.get_vacancy(smm_id) or {}
    safe_v = {k: h(value) if isinstance(value, str) else value for k, value in v.items()}
    rendered = brief_for_vacancy(safe_v)
    assert "<kontent>" not in rendered and "&lt;kontent&gt;" in rendered, "Telegram HTML escaping fix failed"
    assert db.recent_change_logs(10), "Admin change logs empty"

    upload.unlink(missing_ok=True)
    test_db.unlink(missing_ok=True)
    print("SMOKE TEST PASSED: dynamic vacancies, regulation versions, snapshot, materials, logs and HTML safety")


if __name__ == "__main__":
    test()
