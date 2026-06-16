from __future__ import annotations

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.config import settings
from app.database import db, now_str


def _pdf_safe(text: object) -> str:
    s = str(text or "-")
    repl = {
        "‘": "'", "’": "'", "“": '"', "”": '"', "—": "-", "–": "-",
        "o‘": "o'", "O‘": "O'", "g‘": "g'", "G‘": "G'", "ў": "o'", "ғ": "g'",
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


def candidate_pdf_path(candidate_id: int) -> Path:
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    return settings.export_dir / f"candidate_{candidate_id}.pdf"


def _draw_wrapped(c: canvas.Canvas, text: str, x: float, y: float, max_chars: int = 95, line_height: float = 5 * mm) -> float:
    words = _pdf_safe(text).split()
    line = ""
    for word in words:
        if len(line) + len(word) + 1 > max_chars:
            c.drawString(x, y, line)
            y -= line_height
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        c.drawString(x, y, line)
        y -= line_height
    return y


def generate_candidate_pdf(candidate_id: int) -> Path:
    candidate = db.get_candidate(candidate_id)
    if not candidate:
        raise ValueError("Candidate not found")
    work = db.candidate_work_experiences(candidate_id)
    ai = db.get_latest_ai_interview_for_candidate(candidate_id)
    answers = db.ai_answers(ai["id"]) if ai else []
    path = candidate_pdf_path(candidate_id)
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    y = height - 18 * mm

    def header(title: str) -> None:
        nonlocal y
        if y < 35 * mm:
            c.showPage(); y = height - 18 * mm
        c.setFont("Helvetica-Bold", 13)
        c.drawString(15 * mm, y, _pdf_safe(title))
        y -= 8 * mm
        c.setFont("Helvetica", 10)

    def row(label: str, value: object) -> None:
        nonlocal y
        if y < 25 * mm:
            c.showPage(); y = height - 18 * mm; c.setFont("Helvetica", 10)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(15 * mm, y, _pdf_safe(label)[:32] + ":")
        c.setFont("Helvetica", 9)
        y2 = _draw_wrapped(c, str(value or "-"), 62 * mm, y, max_chars=70, line_height=4.5 * mm)
        y = min(y - 5 * mm, y2)

    c.setTitle(f"ALLMAX HR Anketa #{candidate_id}")
    c.setFont("Helvetica-Bold", 16)
    c.drawString(15 * mm, y, _pdf_safe(f"ALLMAX HR ANKETA #{candidate_id}"))
    y -= 10 * mm
    c.setFont("Helvetica", 10)
    row("Ariza sanasi", candidate.get("created_at"))
    row("F.I.SH.", candidate.get("full_name"))
    row("Telefon", candidate.get("phone"))
    row("Telegram ID", candidate.get("telegram_id"))
    row("Username", candidate.get("username"))
    row("Tug'ilgan sana", candidate.get("birth_date"))
    row("Hudud", candidate.get("region"))
    row("Tuman", candidate.get("district"))
    row("Manzil", candidate.get("address"))
    row("Tanlangan lavozim", candidate.get("position"))
    row("Vakansiya ID", candidate.get("vacancy_id"))
    row("Reglament versiya snapshot", candidate.get("regulation_version_snapshot"))
    row("Qabul qilingan bo'lim", candidate.get("accepted_department"))
    row("Ta'lim", candidate.get("education_level"))
    row("Talabami", candidate.get("is_student"))
    row("Tillar", f"UZ: {candidate.get('uzbek_level')}; RU: {candidate.get('russian_level')}; EN: {candidate.get('english_level')}")
    row("Kompyuter", candidate.get("computer_level"))
    row("Ish tajribasi", candidate.get("has_experience"))
    row("Foto", "Bor" if candidate.get("photo_file_id") else "Yo'q")
    row("AI score", candidate.get("ai_score"))
    row("AI grade", candidate.get("ai_grade"))
    row("AI xulosa", candidate.get("ai_summary"))
    row("Admin tavsiya", candidate.get("ai_admin_recommendation"))

    header("Oldingi ish joylari")
    if not work:
        row("Ish tajribasi", "Kiritilmagan")
    for i, w in enumerate(work, 1):
        row(f"Ish joyi {i}", f"{w.get('company_name')} | {w.get('years')} | {w.get('position')} | Ketish sababi: {w.get('leaving_reason')} | Kontakt: {w.get('reference_name')} {w.get('reference_phone')}")

    header("AI intervyu savol-javoblari")
    if not answers:
        row("Intervyu", "Hali o'tkazilmagan")
    for a in answers:
        row(f"{a.get('question_number')}. Savol", a.get("question"))
        row("Javob", a.get("answer"))

    c.setFont("Helvetica", 8)
    c.drawString(15 * mm, 10 * mm, _pdf_safe(f"Generated: {now_str()}"))
    c.save()
    return path
