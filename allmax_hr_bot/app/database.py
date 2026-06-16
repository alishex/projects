from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.utils.validators import digits


def now_str() -> str:
    return datetime.now(settings.tz).strftime("%Y-%m-%d %H:%M:%S")


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def loads(text: str | None, default: Any = None) -> Any:
    if not text:
        return default if default is not None else {}
    try:
        return json.loads(text)
    except Exception:
        return default if default is not None else {}


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE,
                    name TEXT,
                    role TEXT DEFAULT 'admin',
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    username TEXT,
                    language TEXT DEFAULT 'uz',
                    full_name TEXT,
                    birth_date TEXT,
                    phone TEXT,
                    region TEXT,
                    district TEXT,
                    address TEXT,
                    position TEXT,
                    family_status TEXT,
                    is_student TEXT,
                    study_form TEXT,
                    education_place TEXT,
                    course TEXT,
                    study_time TEXT,
                    education_level TEXT,
                    uzbek_level TEXT,
                    russian_level TEXT,
                    english_level TEXT,
                    computer_level TEXT,
                    schedule_ready TEXT,
                    salary_expectation TEXT,
                    vacancy_source TEXT,
                    strong_sides TEXT,
                    weak_sides TEXT,
                    motivation TEXT,
                    possible_start_date TEXT,
                    has_experience TEXT,
                    photo_file_id TEXT,
                    consent INTEGER DEFAULT 0,
                    accepted_department TEXT,
                    ai_score INTEGER DEFAULT 0,
                    ai_grade TEXT,
                    ai_summary TEXT,
                    ai_admin_recommendation TEXT,
                    ai_reasoning TEXT,
                    status TEXT DEFAULT 'draft',
                    duplicate_of_candidate_id INTEGER,
                    admin_note TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS candidate_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    question_key TEXT,
                    question_text TEXT,
                    answer_text TEXT,
                    created_at TEXT,
                    FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS work_experiences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    company_name TEXT,
                    years TEXT,
                    position TEXT,
                    responsibilities TEXT,
                    had_subordinates TEXT,
                    subordinates_count TEXT,
                    leaving_reason TEXT,
                    reference_name TEXT,
                    reference_phone TEXT,
                    data_json TEXT,
                    created_at TEXT,
                    FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS ai_interviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    questions_json TEXT,
                    evaluation_json TEXT,
                    score INTEGER,
                    grade TEXT,
                    created_at TEXT,
                    evaluated_at TEXT,
                    FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS ai_interview_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    interview_id INTEGER,
                    candidate_id INTEGER,
                    question_number INTEGER,
                    question_type TEXT,
                    question TEXT,
                    what_it_checks TEXT,
                    answer TEXT,
                    created_at TEXT,
                    FOREIGN KEY(interview_id) REFERENCES ai_interviews(id) ON DELETE CASCADE,
                    FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS interviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    interview_datetime TEXT,
                    interview_location TEXT,
                    scheduled_by_admin INTEGER,
                    followup_due_at TEXT,
                    followup_status TEXT DEFAULT 'pending',
                    followup_reply TEXT,
                    followup_classification TEXT,
                    status TEXT DEFAULT 'scheduled',
                    created_at TEXT,
                    FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    telegram_id INTEGER,
                    username TEXT,
                    full_name TEXT,
                    phone TEXT,
                    department TEXT,
                    status TEXT DEFAULT 'onboarding',
                    active INTEGER DEFAULT 1,
                    started_at TEXT,
                    completed_at TEXT,
                    admin_note TEXT,
                    FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS onboarding_lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER,
                    department TEXT,
                    lesson_number INTEGER,
                    day_number INTEGER,
                    title TEXT,
                    content_json TEXT,
                    created_at TEXT,
                    UNIQUE(employee_id, lesson_number),
                    FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS onboarding_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER,
                    lesson_number INTEGER,
                    status TEXT DEFAULT 'new',
                    started_at TEXT,
                    completed_at TEXT,
                    test_score_percent REAL,
                    retry_recommended INTEGER DEFAULT 0,
                    UNIQUE(employee_id, lesson_number),
                    FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS lesson_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER,
                    lesson_number INTEGER,
                    questions_json TEXT,
                    answers_json TEXT DEFAULT '{}',
                    correct_answers INTEGER DEFAULT 0,
                    total_questions INTEGER DEFAULT 10,
                    percentage REAL DEFAULT 0,
                    status TEXT DEFAULT 'in_progress',
                    created_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS lesson_test_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lesson_test_id INTEGER,
                    employee_id INTEGER,
                    lesson_number INTEGER,
                    question_number INTEGER,
                    selected_answer TEXT,
                    correct_answer TEXT,
                    is_correct INTEGER,
                    explanation TEXT,
                    created_at TEXT,
                    FOREIGN KEY(lesson_test_id) REFERENCES lesson_tests(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS final_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER,
                    department TEXT,
                    questions_json TEXT,
                    answers_json TEXT DEFAULT '{}',
                    correct_answers INTEGER DEFAULT 0,
                    total_questions INTEGER DEFAULT 30,
                    percentage REAL DEFAULT 0,
                    ai_summary TEXT,
                    admin_recommendation TEXT,
                    evaluation_json TEXT,
                    status TEXT DEFAULT 'in_progress',
                    created_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS final_test_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    final_test_id INTEGER,
                    employee_id INTEGER,
                    question_number INTEGER,
                    selected_answer TEXT,
                    correct_answer TEXT,
                    is_correct INTEGER,
                    explanation TEXT,
                    created_at TEXT,
                    FOREIGN KEY(final_test_id) REFERENCES final_tests(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS candidate_drafts (
                    telegram_id INTEGER PRIMARY KEY,
                    language TEXT DEFAULT 'uz',
                    position TEXT,
                    step TEXT,
                    field_index INTEGER DEFAULT 0,
                    answers_json TEXT DEFAULT '{}',
                    work_json TEXT DEFAULT '[]',
                    created_at TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_telegram_id INTEGER,
                    action TEXT,
                    entity_type TEXT,
                    entity_id INTEGER,
                    details_json TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS clockster_employee_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER UNIQUE,
                    clockster_employee_id TEXT,
                    clockster_full_name TEXT,
                    match_score REAL DEFAULT 0,
                    matched_by TEXT DEFAULT 'auto_name',
                    raw_json TEXT,
                    matched_at TEXT,
                    FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS clockster_attendance_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER,
                    clockster_employee_id TEXT,
                    record_date TEXT,
                    check_in TEXT,
                    check_out TEXT,
                    status TEXT,
                    late_minutes INTEGER DEFAULT 0,
                    work_minutes INTEGER DEFAULT 0,
                    branch TEXT,
                    raw_json TEXT,
                    synced_at TEXT,
                    UNIQUE(employee_id, clockster_employee_id, record_date, check_in, check_out),
                    FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS clockster_sync_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER,
                    status TEXT,
                    message TEXT,
                    details_json TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS vacancies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name_uz TEXT NOT NULL,
                    name_ru TEXT,
                    description_uz TEXT,
                    description_ru TEXT,
                    responsibilities TEXT,
                    requirements TEXT,
                    work_schedule TEXT,
                    interview_question_count INTEGER DEFAULT 10,
                    internship_enabled INTEGER DEFAULT 1,
                    internship_days INTEGER DEFAULT 7,
                    lesson_count INTEGER DEFAULT 20,
                    final_test_count INTEGER DEFAULT 30,
                    status TEXT DEFAULT 'draft',
                    created_by INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS regulations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    regulation_type TEXT,
                    current_version_id INTEGER,
                    status TEXT DEFAULT 'draft',
                    created_by INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS regulation_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    regulation_id INTEGER NOT NULL,
                    version_number INTEGER NOT NULL,
                    original_filename TEXT,
                    stored_file_path TEXT,
                    file_type TEXT,
                    extracted_text TEXT,
                    ai_summary TEXT,
                    change_summary TEXT,
                    uploaded_by INTEGER,
                    uploaded_at TEXT,
                    is_active INTEGER DEFAULT 0,
                    UNIQUE(regulation_id, version_number),
                    FOREIGN KEY(regulation_id) REFERENCES regulations(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS regulation_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    regulation_version_id INTEGER NOT NULL,
                    chunk_number INTEGER NOT NULL,
                    chunk_text TEXT,
                    created_at TEXT,
                    UNIQUE(regulation_version_id, chunk_number),
                    FOREIGN KEY(regulation_version_id) REFERENCES regulation_versions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS vacancy_regulations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vacancy_id INTEGER NOT NULL,
                    regulation_id INTEGER NOT NULL,
                    regulation_version_id INTEGER,
                    use_for_interview INTEGER DEFAULT 1,
                    use_for_lessons INTEGER DEFAULT 1,
                    use_for_tests INTEGER DEFAULT 1,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT,
                    UNIQUE(vacancy_id, regulation_id),
                    FOREIGN KEY(vacancy_id) REFERENCES vacancies(id) ON DELETE CASCADE,
                    FOREIGN KEY(regulation_id) REFERENCES regulations(id) ON DELETE CASCADE,
                    FOREIGN KEY(regulation_version_id) REFERENCES regulation_versions(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS training_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vacancy_id INTEGER NOT NULL,
                    regulation_version_snapshot TEXT,
                    batch_key TEXT,
                    material_type TEXT NOT NULL,
                    material_number INTEGER DEFAULT 0,
                    title TEXT,
                    content TEXT,
                    status TEXT DEFAULT 'draft',
                    generated_by_ai INTEGER DEFAULT 1,
                    approved_by INTEGER,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY(vacancy_id) REFERENCES vacancies(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS question_banks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vacancy_id INTEGER NOT NULL,
                    regulation_version_snapshot TEXT,
                    batch_key TEXT,
                    question_type TEXT NOT NULL,
                    material_number INTEGER DEFAULT 0,
                    question_number INTEGER DEFAULT 0,
                    question_text TEXT,
                    options_json TEXT,
                    correct_answer TEXT,
                    explanation TEXT,
                    status TEXT DEFAULT 'draft',
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY(vacancy_id) REFERENCES vacancies(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS admin_change_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action_type TEXT,
                    entity_type TEXT,
                    entity_id INTEGER,
                    old_value_json TEXT,
                    new_value_json TEXT,
                    created_at TEXT
                );
                """
            )
            self._ensure_column(conn, "employees", "clockster_employee_id", "TEXT")
            self._ensure_column(conn, "employees", "clockster_employee_name", "TEXT")
            self._ensure_column(conn, "employees", "clockster_match_score", "REAL DEFAULT 0")
            self._ensure_column(conn, "employees", "clockster_last_sync_at", "TEXT")
            self._ensure_column(conn, "employees", "clockster_sync_status", "TEXT")
            for table in ["candidates", "employees", "ai_interviews", "onboarding_lessons", "onboarding_progress", "lesson_tests", "final_tests"]:
                self._ensure_column(conn, table, "vacancy_id", "INTEGER")
                self._ensure_column(conn, table, "regulation_version_snapshot", "TEXT")
            self._ensure_column(conn, "candidate_drafts", "vacancy_id", "INTEGER")
            self._ensure_column(conn, "onboarding_lessons", "training_material_id", "INTEGER")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vacancies_status ON vacancies(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_regver_active ON regulation_versions(regulation_id, is_active)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_materials_lookup ON training_materials(vacancy_id, material_type, status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_question_banks_lookup ON question_banks(vacancy_id, question_type, material_number, status)")
            for admin_id in settings.admin_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO admins(telegram_id, name, role, created_at) VALUES (?, ?, 'admin', ?)",
                    (admin_id, "HR Admin", now_str()),
                )
            conn.commit()

    def log(self, actor: int | None, action: str, entity_type: str = "", entity_id: int | None = None, details: Any = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO audit_logs(actor_telegram_id, action, entity_type, entity_id, details_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (actor, action, entity_type, entity_id, dumps(details or {}), now_str()),
            )
            conn.commit()

    def is_admin(self, telegram_id: int) -> bool:
        if telegram_id in settings.admin_ids:
            return True
        with self.connect() as conn:
            row = conn.execute("SELECT id FROM admins WHERE telegram_id=?", (telegram_id,)).fetchone()
        return row is not None

    def save_draft(self, telegram_id: int, language: str, position: str | None, step: str, field_index: int, answers: dict, work: list[dict] | None = None) -> None:
        stamp = now_str()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO candidate_drafts(telegram_id, language, position, step, field_index, answers_json, work_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    language=excluded.language, position=excluded.position, step=excluded.step, field_index=excluded.field_index,
                    answers_json=excluded.answers_json, work_json=excluded.work_json, updated_at=excluded.updated_at
                """,
                (telegram_id, language, position, step, field_index, dumps(answers), dumps(work or []), stamp, stamp),
            )
            conn.commit()

    def get_draft(self, telegram_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM candidate_drafts WHERE telegram_id=?", (telegram_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["answers"] = loads(item.get("answers_json"), {})
        item["work"] = loads(item.get("work_json"), [])
        return item

    def delete_draft(self, telegram_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM candidate_drafts WHERE telegram_id=?", (telegram_id,))
            conn.commit()

    def find_duplicate_phone(self, phone: str | None) -> dict | None:
        target = digits(phone)
        if not target:
            return None
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM candidates WHERE phone IS NOT NULL ORDER BY id DESC").fetchall()
        for row in rows:
            item = dict(row)
            if digits(item.get("phone"))[-9:] == target[-9:]:
                return item
        return None

    def create_candidate(self, data: dict, work_experiences: list[dict] | None = None) -> int:
        stamp = now_str()
        duplicate = self.find_duplicate_phone(data.get("phone"))
        columns = [
            "telegram_id", "username", "language", "full_name", "birth_date", "phone", "region", "district", "address",
            "position", "family_status", "is_student", "study_form", "education_place", "course", "study_time",
            "education_level", "uzbek_level", "russian_level", "english_level", "computer_level", "schedule_ready",
            "salary_expectation", "vacancy_source", "strong_sides", "weak_sides", "motivation", "possible_start_date",
            "has_experience", "photo_file_id", "consent", "vacancy_id", "regulation_version_snapshot", "status", "duplicate_of_candidate_id", "created_at", "updated_at"
        ]
        data = dict(data)
        data.setdefault("status", "interviewing")
        data["duplicate_of_candidate_id"] = duplicate["id"] if duplicate else None
        data["created_at"] = stamp
        data["updated_at"] = stamp
        values = [data.get(c) for c in columns]
        placeholders = ",".join("?" for _ in columns)
        with self.connect() as conn:
            cur = conn.execute(f"INSERT INTO candidates({','.join(columns)}) VALUES ({placeholders})", values)
            cid = int(cur.lastrowid)
            for key, value in data.items():
                if key in {"telegram_id", "username"}:
                    continue
                conn.execute(
                    "INSERT INTO candidate_answers(candidate_id, question_key, question_text, answer_text, created_at) VALUES (?, ?, ?, ?, ?)",
                    (cid, key, key, str(value), stamp),
                )
            for item in work_experiences or []:
                conn.execute(
                    """
                    INSERT INTO work_experiences(candidate_id, company_name, years, position, responsibilities, had_subordinates,
                    subordinates_count, leaving_reason, reference_name, reference_phone, data_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cid, item.get("company_name"), item.get("years"), item.get("position"), item.get("responsibilities"),
                        item.get("had_subordinates"), item.get("subordinates_count"), item.get("leaving_reason"),
                        item.get("reference_name"), item.get("reference_phone"), dumps(item), stamp,
                    ),
                )
            conn.commit()
        self.log(data.get("telegram_id"), "candidate_created", "candidate", cid, {"position": data.get("position")})
        return cid

    def get_candidate(self, candidate_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()
        return dict(row) if row else None

    def get_candidate_by_telegram(self, telegram_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM candidates WHERE telegram_id=? ORDER BY id DESC LIMIT 1", (telegram_id,)).fetchone()
        return dict(row) if row else None

    def update_candidate(self, candidate_id: int, **updates: Any) -> None:
        if not updates:
            return
        updates["updated_at"] = now_str()
        parts = ", ".join(f"{key}=?" for key in updates)
        params = list(updates.values()) + [candidate_id]
        with self.connect() as conn:
            conn.execute(f"UPDATE candidates SET {parts} WHERE id=?", params)
            conn.commit()

    def list_candidates(self, section: str = "new", limit: int = 20) -> list[dict]:
        query = "SELECT * FROM candidates"
        params: list[Any] = []
        where = ""
        if section == "new":
            where = " WHERE status IN ('submitted','interviewing')"
        elif section == "ai_rejected":
            where = " WHERE status='ai_rejected' OR ai_grade='low'"
        elif section == "medium":
            where = " WHERE ai_grade='medium'"
        elif section == "excellent":
            where = " WHERE ai_grade='excellent'"
        elif section == "invited":
            where = " WHERE status='invited'"
        elif section == "accepted":
            where = " WHERE status='accepted'"
        elif section == "rejected":
            where = " WHERE status='rejected'"
        elif section == "reserve":
            where = " WHERE status='reserve'"
        query += where + " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def candidate_work_experiences(self, candidate_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM work_experiences WHERE candidate_id=? ORDER BY id", (candidate_id,)).fetchall()
        return [dict(r) for r in rows]

    def create_ai_interview(self, candidate_id: int, questions: list[dict]) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO ai_interviews(candidate_id, questions_json, vacancy_id, regulation_version_snapshot, created_at) VALUES (?, ?, ?, ?, ?)",
                (candidate_id, dumps({"questions": questions}), candidate.get("vacancy_id") if (candidate := self.get_candidate(candidate_id)) else None, candidate.get("regulation_version_snapshot") if candidate else None, now_str()),
            )
            conn.commit()
            return int(cur.lastrowid)

    def get_ai_interview(self, interview_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM ai_interviews WHERE id=?", (interview_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["questions"] = loads(item.get("questions_json"), {"questions": []}).get("questions", [])
        item["evaluation"] = loads(item.get("evaluation_json"), {})
        return item

    def get_latest_ai_interview_for_candidate(self, candidate_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM ai_interviews WHERE candidate_id=? ORDER BY id DESC LIMIT 1", (candidate_id,)).fetchone()
        if not row:
            return None
        return self.get_ai_interview(int(row["id"]))

    def save_ai_answer(self, interview_id: int, candidate_id: int, q: dict, answer: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO ai_interview_answers(interview_id, candidate_id, question_number, question_type, question, what_it_checks, answer, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (interview_id, candidate_id, q.get("number"), q.get("type"), q.get("question"), q.get("what_it_checks"), answer, now_str()),
            )
            conn.commit()

    def ai_answers(self, interview_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM ai_interview_answers WHERE interview_id=? ORDER BY question_number", (interview_id,)).fetchall()
        return [dict(r) for r in rows]

    def save_ai_evaluation(self, interview_id: int, candidate_id: int, evaluation: dict) -> None:
        score = int(evaluation.get("score") or 0)
        grade = evaluation.get("grade") or ("low" if score < 60 else "medium" if score < 80 else "excellent")
        status = "ai_rejected" if score < 60 else "submitted"
        with self.connect() as conn:
            conn.execute(
                "UPDATE ai_interviews SET evaluation_json=?, score=?, grade=?, evaluated_at=? WHERE id=?",
                (dumps(evaluation), score, grade, now_str(), interview_id),
            )
            conn.execute(
                """
                UPDATE candidates SET ai_score=?, ai_grade=?, ai_summary=?, ai_admin_recommendation=?, ai_reasoning=?, status=?, updated_at=? WHERE id=?
                """,
                (
                    score, grade, evaluation.get("summary"), evaluation.get("admin_recommendation"),
                    evaluation.get("reasoning_for_admin"), status, now_str(), candidate_id,
                ),
            )
            conn.commit()
        self.log(None, "ai_evaluated", "candidate", candidate_id, evaluation)

    def schedule_interview(self, candidate_id: int, dt_text: str, location: str, admin_id: int, followup_due_at: str) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO interviews(candidate_id, interview_datetime, interview_location, scheduled_by_admin, followup_due_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (candidate_id, dt_text, location, admin_id, followup_due_at, now_str()),
            )
            conn.execute("UPDATE candidates SET status='invited', updated_at=? WHERE id=?", (now_str(), candidate_id))
            conn.commit()
            return int(cur.lastrowid)

    def due_followups(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM interviews WHERE followup_status='pending' AND followup_due_at IS NOT NULL").fetchall()
        return [dict(r) for r in rows]

    def get_interview(self, interview_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM interviews WHERE id=?", (interview_id,)).fetchone()
        return dict(row) if row else None

    def pending_followup_for_user(self, telegram_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT interviews.* FROM interviews
                JOIN candidates ON candidates.id=interviews.candidate_id
                WHERE candidates.telegram_id=? AND interviews.followup_status='asked'
                ORDER BY interviews.id DESC LIMIT 1
                """,
                (telegram_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_interview(self, interview_id: int, **updates: Any) -> None:
        if not updates:
            return
        parts = ", ".join(f"{k}=?" for k in updates)
        with self.connect() as conn:
            conn.execute(f"UPDATE interviews SET {parts} WHERE id=?", list(updates.values()) + [interview_id])
            conn.commit()

    def create_employee(self, candidate_id: int, department: str) -> int:
        candidate = self.get_candidate(candidate_id)
        if not candidate:
            raise ValueError("Candidate not found")
        existing = self.get_employee_by_candidate(candidate_id)
        if existing:
            self.update_candidate(candidate_id, status="accepted", accepted_department=department)
            return int(existing["id"])
        selected_vacancy = self.get_vacancy_by_name(department)
        vacancy_id = int(selected_vacancy["id"]) if selected_vacancy else candidate.get("vacancy_id")
        snapshot = candidate.get("regulation_version_snapshot")
        if vacancy_id and int(vacancy_id) != int(candidate.get("vacancy_id") or 0):
            snapshot = self.regulation_snapshot(int(vacancy_id))
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO employees(candidate_id, telegram_id, username, full_name, phone, department, vacancy_id, regulation_version_snapshot, status, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'onboarding', ?)
                """,
                (candidate_id, candidate.get("telegram_id"), candidate.get("username"), candidate.get("full_name"), candidate.get("phone"), department, vacancy_id, snapshot, now_str()),
            )
            employee_id = int(cur.lastrowid)
            conn.execute(
                "UPDATE candidates SET status='accepted', accepted_department=?, updated_at=? WHERE id=?",
                (department, now_str(), candidate_id),
            )
            conn.commit()
        self.log(None, "employee_created", "employee", employee_id, {"candidate_id": candidate_id, "department": department})
        return employee_id

    def get_employee(self, employee_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()
        return dict(row) if row else None

    def get_employee_by_candidate(self, candidate_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM employees WHERE candidate_id=?", (candidate_id,)).fetchone()
        return dict(row) if row else None

    def get_employee_by_telegram(self, telegram_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM employees WHERE telegram_id=? AND active=1 ORDER BY id DESC LIMIT 1", (telegram_id,)).fetchone()
        return dict(row) if row else None

    def list_employees(self, status: str | None = None, limit: int = 50) -> list[dict]:
        query = "SELECT * FROM employees"
        params: list[Any] = []
        if status:
            query += " WHERE status=?"
            params.append(status)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def upsert_lesson(self, employee_id: int, department: str, lesson_number: int, day_number: int, title: str, content: dict) -> int:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO onboarding_lessons(employee_id, department, lesson_number, day_number, title, content_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(employee_id, lesson_number) DO UPDATE SET title=excluded.title, content_json=excluded.content_json
                """,
                (employee_id, department, lesson_number, day_number, title, dumps(content), now_str()),
            )
            row = conn.execute("SELECT id FROM onboarding_lessons WHERE employee_id=? AND lesson_number=?", (employee_id, lesson_number)).fetchone()
            conn.execute(
                "INSERT OR IGNORE INTO onboarding_progress(employee_id, lesson_number, status) VALUES (?, ?, 'new')",
                (employee_id, lesson_number),
            )
            conn.commit()
            return int(row["id"])

    def get_lesson(self, employee_id: int, lesson_number: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM onboarding_lessons WHERE employee_id=? AND lesson_number=?", (employee_id, lesson_number)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["content"] = loads(item.get("content_json"), {})
        return item

    def lesson_progress(self, employee_id: int, lesson_number: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM onboarding_progress WHERE employee_id=? AND lesson_number=?", (employee_id, lesson_number)).fetchone()
        return dict(row) if row else None

    def update_lesson_progress(self, employee_id: int, lesson_number: int, **updates: Any) -> None:
        if not updates:
            return
        keys = ", ".join(f"{k}=?" for k in updates)
        with self.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO onboarding_progress(employee_id, lesson_number, status) VALUES (?, ?, 'new')",
                (employee_id, lesson_number),
            )
            conn.execute(f"UPDATE onboarding_progress SET {keys} WHERE employee_id=? AND lesson_number=?", list(updates.values()) + [employee_id, lesson_number])
            conn.commit()

    def completed_lessons_count(self, employee_id: int) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM onboarding_progress WHERE employee_id=? AND status='completed'", (employee_id,)).fetchone()
        return int(row["c"] if row else 0)

    def create_lesson_test(self, employee_id: int, lesson_number: int, questions: list[dict]) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO lesson_tests(employee_id, lesson_number, questions_json, total_questions, created_at) VALUES (?, ?, ?, ?, ?)",
                (employee_id, lesson_number, dumps({"questions": questions}), len(questions), now_str()),
            )
            conn.commit()
            return int(cur.lastrowid)

    def get_lesson_test(self, test_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM lesson_tests WHERE id=?", (test_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["questions"] = loads(item.get("questions_json"), {"questions": []}).get("questions", [])
        item["answers"] = loads(item.get("answers_json"), {})
        return item

    def save_lesson_test_answer(self, test_id: int, question_number: int, selected: str) -> dict:
        test = self.get_lesson_test(test_id)
        if not test:
            raise ValueError("Test not found")
        questions = test["questions"]
        q = questions[question_number - 1]
        correct = str(q.get("correct_answer", "")).upper()
        selected = selected.upper()
        is_correct = int(selected == correct)
        answers = dict(test.get("answers") or {})
        if str(question_number) in answers:
            return {"already": True, "is_correct": bool(answers[str(question_number)].get("is_correct")), "correct": correct, "question": q}
        answers[str(question_number)] = {"selected": selected, "correct": correct, "is_correct": bool(is_correct)}
        correct_count = sum(1 for item in answers.values() if item.get("is_correct"))
        total = len(questions)
        status = "completed" if len(answers) >= total else "in_progress"
        percent = round(correct_count * 100 / total, 2) if total else 0
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO lesson_test_answers(lesson_test_id, employee_id, lesson_number, question_number, selected_answer, correct_answer, is_correct, explanation, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (test_id, test["employee_id"], test["lesson_number"], question_number, selected, correct, is_correct, q.get("explanation"), now_str()),
            )
            conn.execute(
                "UPDATE lesson_tests SET answers_json=?, correct_answers=?, percentage=?, status=?, completed_at=? WHERE id=?",
                (dumps(answers), correct_count, percent, status, now_str() if status == "completed" else None, test_id),
            )
            if status == "completed":
                conn.execute(
                    "UPDATE onboarding_progress SET status='completed', completed_at=?, test_score_percent=?, retry_recommended=? WHERE employee_id=? AND lesson_number=?",
                    (now_str(), percent, 1 if percent < 60 else 0, test["employee_id"], test["lesson_number"]),
                )
            conn.commit()
        return {"already": False, "is_correct": bool(is_correct), "correct": correct, "question": q, "completed": status == "completed", "percent": percent, "correct_count": correct_count, "total": total}

    def create_final_test(self, employee_id: int, department: str, questions: list[dict]) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO final_tests(employee_id, department, questions_json, total_questions, created_at) VALUES (?, ?, ?, ?, ?)",
                (employee_id, department, dumps({"questions": questions}), len(questions), now_str()),
            )
            conn.commit()
            return int(cur.lastrowid)

    def get_final_test(self, final_test_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM final_tests WHERE id=?", (final_test_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["questions"] = loads(item.get("questions_json"), {"questions": []}).get("questions", [])
        item["answers"] = loads(item.get("answers_json"), {})
        item["evaluation"] = loads(item.get("evaluation_json"), {})
        return item

    def save_final_test_answer(self, final_test_id: int, question_number: int, selected: str) -> dict:
        test = self.get_final_test(final_test_id)
        if not test:
            raise ValueError("Final test not found")
        questions = test["questions"]
        q = questions[question_number - 1]
        correct = str(q.get("correct_answer", "")).upper()
        selected = selected.upper()
        is_correct = int(selected == correct)
        answers = dict(test.get("answers") or {})
        if str(question_number) in answers:
            return {"already": True, "is_correct": bool(answers[str(question_number)].get("is_correct")), "correct": correct, "question": q}
        answers[str(question_number)] = {"selected": selected, "correct": correct, "is_correct": bool(is_correct)}
        correct_count = sum(1 for item in answers.values() if item.get("is_correct"))
        total = len(questions)
        status = "completed" if len(answers) >= total else "in_progress"
        percent = round(correct_count * 100 / total, 2) if total else 0
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO final_test_answers(final_test_id, employee_id, question_number, selected_answer, correct_answer, is_correct, explanation, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (final_test_id, test["employee_id"], question_number, selected, correct, is_correct, q.get("explanation"), now_str()),
            )
            conn.execute(
                "UPDATE final_tests SET answers_json=?, correct_answers=?, percentage=?, status=?, completed_at=? WHERE id=?",
                (dumps(answers), correct_count, percent, status, now_str() if status == "completed" else None, final_test_id),
            )
            if status == "completed":
                conn.execute("UPDATE employees SET status='active', completed_at=? WHERE id=?", (now_str(), test["employee_id"]))
            conn.commit()
        return {"already": False, "is_correct": bool(is_correct), "correct": correct, "question": q, "completed": status == "completed", "percent": percent, "correct_count": correct_count, "total": total}

    def save_final_evaluation(self, final_test_id: int, evaluation: dict) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE final_tests SET evaluation_json=?, ai_summary=?, admin_recommendation=? WHERE id=?",
                (dumps(evaluation), evaluation.get("message_to_admin") or evaluation.get("responsibility_comment"), evaluation.get("admin_recommendation"), final_test_id),
            )
            conn.commit()

    def lesson_test_stats(self, employee_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM lesson_tests WHERE employee_id=? AND status='completed' ORDER BY lesson_number", (employee_id,)).fetchall()
        return [dict(r) for r in rows]

    def final_tests(self, limit: int = 50) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM final_tests ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def save_clockster_sync_log(self, employee_id: int | None, status: str, message: str, details: Any = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO clockster_sync_logs(employee_id, status, message, details_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (employee_id, status, message, dumps(details or {}), now_str()),
            )
            conn.commit()

    def save_clockster_link(self, employee_id: int, clockster_employee_id: str, clockster_full_name: str, match_score: float, raw: Any = None, matched_by: str = "auto_name") -> None:
        stamp = now_str()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO clockster_employee_links(employee_id, clockster_employee_id, clockster_full_name, match_score, matched_by, raw_json, matched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(employee_id) DO UPDATE SET
                    clockster_employee_id=excluded.clockster_employee_id,
                    clockster_full_name=excluded.clockster_full_name,
                    match_score=excluded.match_score,
                    matched_by=excluded.matched_by,
                    raw_json=excluded.raw_json,
                    matched_at=excluded.matched_at
                """,
                (employee_id, clockster_employee_id, clockster_full_name, match_score, matched_by, dumps(raw or {}), stamp),
            )
            conn.execute(
                "UPDATE employees SET clockster_employee_id=?, clockster_employee_name=?, clockster_match_score=?, clockster_sync_status='linked', clockster_last_sync_at=? WHERE id=?",
                (clockster_employee_id, clockster_full_name, match_score, stamp, employee_id),
            )
            conn.commit()

    def get_clockster_link(self, employee_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM clockster_employee_links WHERE employee_id=?", (employee_id,)).fetchone()
        return dict(row) if row else None

    def save_clockster_attendance_records(self, employee_id: int, clockster_employee_id: str, records: list[dict]) -> int:
        stamp = now_str()
        count = 0
        with self.connect() as conn:
            for r in records:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO clockster_attendance_records(
                        employee_id, clockster_employee_id, record_date, check_in, check_out, status,
                        late_minutes, work_minutes, branch, raw_json, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        employee_id,
                        clockster_employee_id,
                        r.get("record_date"),
                        r.get("check_in"),
                        r.get("check_out"),
                        r.get("status"),
                        int(r.get("late_minutes") or 0),
                        int(r.get("work_minutes") or 0),
                        r.get("branch"),
                        dumps(r.get("raw") or r),
                        stamp,
                    ),
                )
                count += 1
            conn.execute("UPDATE employees SET clockster_last_sync_at=?, clockster_sync_status='synced' WHERE id=?", (stamp, employee_id))
            conn.commit()
        return count

    def clockster_attendance_for_employee(self, employee_id: int, limit: int = 20) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM clockster_attendance_records
                WHERE employee_id=?
                ORDER BY COALESCE(check_in, record_date) DESC, id DESC
                LIMIT ?
                """,
                (employee_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def clockster_dashboard(self, limit: int = 50) -> list[dict]:
        with self.connect() as conn:
            employees = conn.execute(
                """
                SELECT * FROM employees
                WHERE active=1 AND status='active' AND completed_at IS NOT NULL
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            result: list[dict] = []
            for e in employees:
                latest = conn.execute(
                    """
                    SELECT * FROM clockster_attendance_records
                    WHERE employee_id=?
                    ORDER BY COALESCE(check_in, record_date) DESC, id DESC
                    LIMIT 1
                    """,
                    (e["id"],),
                ).fetchone()
                item = dict(e)
                item["latest_attendance"] = dict(latest) if latest else None
                result.append(item)
        return result

    def clockster_recent_sync_logs(self, limit: int = 10) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM clockster_sync_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


    # -------------------- Dynamic vacancy / regulation catalog --------------------
    def change_log(self, admin_id: int | None, action: str, entity_type: str, entity_id: int | None, old: Any = None, new: Any = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO admin_change_logs(admin_id, action_type, entity_type, entity_id, old_value_json, new_value_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (admin_id, action, entity_type, entity_id, dumps(old or {}), dumps(new or {}), now_str()),
            )
            conn.commit()
        self.log(admin_id, action, entity_type, entity_id, {"old": old or {}, "new": new or {}})

    def create_vacancy(self, data: dict, admin_id: int | None = None) -> int:
        stamp = now_str()
        values = {
            "name_uz": (data.get("name_uz") or "").strip(), "name_ru": (data.get("name_ru") or "").strip(),
            "description_uz": data.get("description_uz") or "", "description_ru": data.get("description_ru") or "",
            "responsibilities": data.get("responsibilities") or "", "requirements": data.get("requirements") or "",
            "work_schedule": data.get("work_schedule") or "", "interview_question_count": int(data.get("interview_question_count") or 10),
            "internship_enabled": int(bool(data.get("internship_enabled", True))), "internship_days": int(data.get("internship_days") or 7),
            "lesson_count": int(data.get("lesson_count") or 20), "final_test_count": int(data.get("final_test_count") or 30),
            "status": data.get("status") or "draft", "created_by": admin_id, "created_at": stamp, "updated_at": stamp,
        }
        if not values["name_uz"]:
            raise ValueError("Vakansiya nomi bo‘sh bo‘lishi mumkin emas")
        with self.connect() as conn:
            existing = conn.execute("SELECT id FROM vacancies WHERE lower(name_uz)=lower(?)", (values["name_uz"],)).fetchone()
            if existing:
                return int(existing["id"])
            columns = list(values)
            cur = conn.execute(f"INSERT INTO vacancies({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", [values[c] for c in columns])
            vid = int(cur.lastrowid)
            conn.commit()
        self.change_log(admin_id, "vacancy_created", "vacancy", vid, {}, values)
        return vid

    def get_vacancy(self, vacancy_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM vacancies WHERE id=?", (vacancy_id,)).fetchone()
        return dict(row) if row else None

    def get_vacancy_by_name(self, name: str | None) -> dict | None:
        if not name:
            return None
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM vacancies WHERE name_uz=? OR name_ru=? ORDER BY id LIMIT 1", (name, name)).fetchone()
        return dict(row) if row else None

    def list_vacancies(self, status: str | None = None, include_archived: bool = True) -> list[dict]:
        q = "SELECT * FROM vacancies"
        args: list[Any] = []
        if status:
            q += " WHERE status=?"; args.append(status)
        elif not include_archived:
            q += " WHERE status<>'archived'"
        q += " ORDER BY CASE status WHEN 'active' THEN 1 WHEN 'draft' THEN 2 WHEN 'hidden' THEN 3 ELSE 4 END, id"
        with self.connect() as conn:
            rows = conn.execute(q, args).fetchall()
        return [dict(r) for r in rows]

    def update_vacancy(self, vacancy_id: int, admin_id: int | None = None, **updates: Any) -> None:
        allowed = {"name_uz", "name_ru", "description_uz", "description_ru", "responsibilities", "requirements", "work_schedule", "interview_question_count", "internship_enabled", "internship_days", "lesson_count", "final_test_count", "status"}
        clean = {k: v for k, v in updates.items() if k in allowed}
        if not clean:
            return
        old = self.get_vacancy(vacancy_id) or {}
        clean["updated_at"] = now_str()
        with self.connect() as conn:
            conn.execute("UPDATE vacancies SET " + ", ".join(f"{k}=?" for k in clean) + " WHERE id=?", [*clean.values(), vacancy_id])
            conn.commit()
        self.change_log(admin_id, "vacancy_updated", "vacancy", vacancy_id, old, clean)

    def create_regulation(self, title: str, regulation_type: str, admin_id: int | None = None) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT id FROM regulations WHERE lower(title)=lower(?)", (title.strip(),)).fetchone()
            if row:
                return int(row["id"])
            cur = conn.execute("INSERT INTO regulations(title, regulation_type, status, created_by, created_at, updated_at) VALUES (?, ?, 'draft', ?, ?, ?)", (title.strip(), regulation_type, admin_id, now_str(), now_str()))
            rid = int(cur.lastrowid); conn.commit()
        self.change_log(admin_id, "regulation_created", "regulation", rid, {}, {"title": title, "regulation_type": regulation_type})
        return rid

    def get_regulation(self, regulation_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM regulations WHERE id=?", (regulation_id,)).fetchone()
        return dict(row) if row else None

    def list_regulations(self, include_archived: bool = True) -> list[dict]:
        q = "SELECT r.*, rv.version_number AS current_version_number FROM regulations r LEFT JOIN regulation_versions rv ON rv.id=r.current_version_id"
        if not include_archived:
            q += " WHERE r.status<>'archived'"
        q += " ORDER BY r.id DESC"
        with self.connect() as conn:
            rows = conn.execute(q).fetchall()
        return [dict(r) for r in rows]

    def add_regulation_version(self, regulation_id: int, original_filename: str, stored_path: str, file_type: str, extracted_text: str, ai_summary: str, change_summary: str, admin_id: int | None = None, active: bool = False) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(version_number),0)+1 AS n FROM regulation_versions WHERE regulation_id=?", (regulation_id,)).fetchone()
            number = int(row["n"])
            cur = conn.execute("""INSERT INTO regulation_versions(regulation_id, version_number, original_filename, stored_file_path, file_type, extracted_text, ai_summary, change_summary, uploaded_by, uploaded_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (regulation_id, number, original_filename, stored_path, file_type, extracted_text, ai_summary, change_summary, admin_id, now_str(), int(active)))
            version_id = int(cur.lastrowid)
            for i, chunk in enumerate([extracted_text[j:j+5000] for j in range(0, len(extracted_text), 5000)] or [""], 1):
                conn.execute("INSERT INTO regulation_chunks(regulation_version_id, chunk_number, chunk_text, created_at) VALUES (?, ?, ?, ?)", (version_id, i, chunk, now_str()))
            conn.commit()
        if active:
            self.activate_regulation_version(version_id, admin_id)
        else:
            self.change_log(admin_id, "regulation_version_uploaded", "regulation_version", version_id, {}, {"regulation_id": regulation_id, "version": number})
        return version_id

    def get_regulation_version(self, version_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT rv.*, r.title, r.regulation_type FROM regulation_versions rv JOIN regulations r ON r.id=rv.regulation_id WHERE rv.id=?", (version_id,)).fetchone()
        return dict(row) if row else None

    def regulation_versions(self, regulation_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM regulation_versions WHERE regulation_id=? ORDER BY version_number DESC", (regulation_id,)).fetchall()
        return [dict(r) for r in rows]

    def activate_regulation_version(self, version_id: int, admin_id: int | None = None) -> None:
        version = self.get_regulation_version(version_id)
        if not version:
            raise ValueError("Reglament versiyasi topilmadi")
        rid = int(version["regulation_id"])
        old = self.get_regulation(rid) or {}
        with self.connect() as conn:
            conn.execute("UPDATE regulation_versions SET is_active=0 WHERE regulation_id=?", (rid,))
            conn.execute("UPDATE regulation_versions SET is_active=1 WHERE id=?", (version_id,))
            conn.execute("UPDATE regulations SET current_version_id=?, status='active', updated_at=? WHERE id=?", (version_id, now_str(), rid))
            conn.execute("UPDATE vacancy_regulations SET regulation_version_id=? WHERE regulation_id=? AND is_active=1", (version_id, rid))
            conn.commit()
        self.change_log(admin_id, "regulation_version_activated", "regulation", rid, old, {"current_version_id": version_id, "version_number": version.get("version_number")})

    def archive_regulation(self, regulation_id: int, admin_id: int | None = None) -> None:
        old = self.get_regulation(regulation_id) or {}
        with self.connect() as conn:
            conn.execute("UPDATE regulations SET status='archived', updated_at=? WHERE id=?", (now_str(), regulation_id))
            conn.execute("UPDATE vacancy_regulations SET is_active=0 WHERE regulation_id=?", (regulation_id,))
            conn.commit()
        self.change_log(admin_id, "regulation_archived", "regulation", regulation_id, old, {"status": "archived"})

    def link_vacancy_regulation(self, vacancy_id: int, regulation_id: int, admin_id: int | None = None, version_id: int | None = None, use_for_interview: bool = True, use_for_lessons: bool = True, use_for_tests: bool = True) -> None:
        if version_id is None:
            reg = self.get_regulation(regulation_id) or {}
            version_id = reg.get("current_version_id")
        values = (int(bool(use_for_interview)), int(bool(use_for_lessons)), int(bool(use_for_tests)))
        with self.connect() as conn:
            oldrow = conn.execute("SELECT * FROM vacancy_regulations WHERE vacancy_id=? AND regulation_id=?", (vacancy_id, regulation_id)).fetchone()
            conn.execute("""INSERT INTO vacancy_regulations(vacancy_id, regulation_id, regulation_version_id, use_for_interview, use_for_lessons, use_for_tests, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?) ON CONFLICT(vacancy_id, regulation_id) DO UPDATE SET regulation_version_id=excluded.regulation_version_id, use_for_interview=excluded.use_for_interview, use_for_lessons=excluded.use_for_lessons, use_for_tests=excluded.use_for_tests, is_active=1""", (vacancy_id, regulation_id, version_id, *values, now_str()))
            conn.commit()
        self.change_log(admin_id, "vacancy_regulation_linked", "vacancy", vacancy_id, dict(oldrow) if oldrow else {}, {"regulation_id": regulation_id, "version_id": version_id, "uses": values})

    def unlink_vacancy_regulation(self, vacancy_id: int, regulation_id: int, admin_id: int | None = None) -> None:
        with self.connect() as conn:
            old = conn.execute("SELECT * FROM vacancy_regulations WHERE vacancy_id=? AND regulation_id=?", (vacancy_id, regulation_id)).fetchone()
            conn.execute("UPDATE vacancy_regulations SET is_active=0 WHERE vacancy_id=? AND regulation_id=?", (vacancy_id, regulation_id))
            conn.commit()
        self.change_log(admin_id, "vacancy_regulation_unlinked", "vacancy", vacancy_id, dict(old) if old else {}, {"regulation_id": regulation_id, "is_active": 0})

    def vacancy_regulation_links(self, vacancy_id: int, purpose: str | None = None) -> list[dict]:
        extra = ""
        if purpose == "interview": extra = " AND vr.use_for_interview=1"
        elif purpose == "lessons": extra = " AND vr.use_for_lessons=1"
        elif purpose == "tests": extra = " AND vr.use_for_tests=1"
        with self.connect() as conn:
            rows = conn.execute("""SELECT vr.*, r.title, r.regulation_type, rv.version_number, rv.extracted_text, rv.ai_summary FROM vacancy_regulations vr JOIN regulations r ON r.id=vr.regulation_id LEFT JOIN regulation_versions rv ON rv.id=COALESCE(vr.regulation_version_id, r.current_version_id) WHERE vr.vacancy_id=? AND vr.is_active=1 AND r.status='active'""" + extra + " ORDER BY r.id", (vacancy_id,)).fetchall()
        return [dict(r) for r in rows]

    def vacancies_for_regulation(self, regulation_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT v.* FROM vacancies v JOIN vacancy_regulations vr ON vr.vacancy_id=v.id WHERE vr.regulation_id=? AND vr.is_active=1 ORDER BY v.id", (regulation_id,)).fetchall()
        return [dict(r) for r in rows]

    def regulation_snapshot(self, vacancy_id: int) -> str:
        links = self.vacancy_regulation_links(vacancy_id)
        items = [{"regulation_id": x["regulation_id"], "version_id": x.get("regulation_version_id"), "version_number": x.get("version_number"), "title": x.get("title"), "use_for_interview": x.get("use_for_interview"), "use_for_lessons": x.get("use_for_lessons"), "use_for_tests": x.get("use_for_tests")} for x in links]
        return dumps(items)

    def save_training_material(self, vacancy_id: int, snapshot: str, batch_key: str, material_type: str, number: int, title: str, content: Any, admin_id: int | None = None, generated_by_ai: bool = True) -> int:
        with self.connect() as conn:
            cur = conn.execute("INSERT INTO training_materials(vacancy_id, regulation_version_snapshot, batch_key, material_type, material_number, title, content, status, generated_by_ai, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?)", (vacancy_id, snapshot, batch_key, material_type, number, title, dumps(content) if not isinstance(content, str) else content, int(generated_by_ai), now_str(), now_str()))
            mid = int(cur.lastrowid); conn.commit()
        return mid

    def save_question_bank(self, vacancy_id: int, snapshot: str, batch_key: str, question_type: str, material_number: int, questions: list[dict], status: str = "draft") -> None:
        with self.connect() as conn:
            for qn, q in enumerate(questions, 1):
                conn.execute("INSERT INTO question_banks(vacancy_id, regulation_version_snapshot, batch_key, question_type, material_number, question_number, question_text, options_json, correct_answer, explanation, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (vacancy_id, snapshot, batch_key, question_type, material_number, qn, q.get("question"), dumps(q.get("options") or {}), q.get("correct_answer"), q.get("explanation"), status, now_str(), now_str()))
            conn.commit()

    def list_training_materials(self, vacancy_id: int | None = None, status: str | None = None, material_type: str | None = None, limit: int = 300) -> list[dict]:
        where=[]; args=[]
        if vacancy_id is not None: where.append("vacancy_id=?"); args.append(vacancy_id)
        if status is not None: where.append("status=?"); args.append(status)
        if material_type is not None: where.append("material_type=?"); args.append(material_type)
        q="SELECT * FROM training_materials" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY batch_key DESC, material_number LIMIT ?"; args.append(limit)
        with self.connect() as conn:
            rows=conn.execute(q,args).fetchall()
        return [dict(r) for r in rows]

    def active_material(self, vacancy_id: int, material_type: str, number: int = 0, snapshot: str | None = None) -> dict | None:
        q="SELECT * FROM training_materials WHERE vacancy_id=? AND material_type=? AND material_number=? AND status='active'"; args=[vacancy_id, material_type, number]
        if snapshot: q += " AND regulation_version_snapshot=?"; args.append(snapshot)
        q += " ORDER BY id DESC LIMIT 1"
        with self.connect() as conn: row=conn.execute(q,args).fetchone()
        return dict(row) if row else None

    def active_questions(self, vacancy_id: int, question_type: str, material_number: int = 0, snapshot: str | None = None) -> list[dict]:
        q="SELECT * FROM question_banks WHERE vacancy_id=? AND question_type=? AND material_number=? AND status='active'"; args=[vacancy_id, question_type, material_number]
        if snapshot: q += " AND regulation_version_snapshot=?"; args.append(snapshot)
        q += " ORDER BY question_number"
        with self.connect() as conn: rows=conn.execute(q,args).fetchall()
        return [{"question": r["question_text"], "options": loads(r["options_json"], {}), "correct_answer": r["correct_answer"], "explanation": r["explanation"]} for r in rows]

    def activate_material_batch(self, vacancy_id: int, batch_key: str, admin_id: int | None = None) -> None:
        with self.connect() as conn:
            types=[r["material_type"] for r in conn.execute("SELECT DISTINCT material_type FROM training_materials WHERE vacancy_id=? AND batch_key=?", (vacancy_id,batch_key)).fetchall()]
            qtypes=[r["question_type"] for r in conn.execute("SELECT DISTINCT question_type FROM question_banks WHERE vacancy_id=? AND batch_key=?", (vacancy_id,batch_key)).fetchall()]
            for typ in types: conn.execute("UPDATE training_materials SET status='archived', updated_at=? WHERE vacancy_id=? AND material_type=? AND status='active'", (now_str(), vacancy_id, typ))
            for typ in qtypes: conn.execute("UPDATE question_banks SET status='archived', updated_at=? WHERE vacancy_id=? AND question_type=? AND status='active'", (now_str(), vacancy_id, typ))
            conn.execute("UPDATE training_materials SET status='active', approved_by=?, updated_at=? WHERE vacancy_id=? AND batch_key=?", (admin_id, now_str(), vacancy_id, batch_key))
            conn.execute("UPDATE question_banks SET status='active', updated_at=? WHERE vacancy_id=? AND batch_key=?", (now_str(), vacancy_id, batch_key))
            conn.commit()
        self.change_log(admin_id, "materials_activated", "vacancy", vacancy_id, {}, {"batch_key": batch_key})

    def update_training_material(self, material_id: int, admin_id: int | None = None, **updates: Any) -> None:
        allowed={"title","content","status"}; clean={k:v for k,v in updates.items() if k in allowed}
        if not clean: return
        clean["updated_at"]=now_str()
        with self.connect() as conn:
            old=conn.execute("SELECT * FROM training_materials WHERE id=?",(material_id,)).fetchone()
            conn.execute("UPDATE training_materials SET " + ", ".join(f"{k}=?" for k in clean) + " WHERE id=?", [*clean.values(), material_id]); conn.commit()
        self.change_log(admin_id,"material_updated","training_material",material_id,dict(old) if old else {},clean)

    def list_question_bank_rows(self, vacancy_id: int, question_type: str | None = None, status: str | None = None, limit: int = 60) -> list[dict]:
        where=["vacancy_id=?"]; args: list[Any]=[vacancy_id]
        if question_type:
            where.append("question_type=?"); args.append(question_type)
        if status:
            where.append("status=?"); args.append(status)
        q="SELECT * FROM question_banks WHERE " + " AND ".join(where) + " ORDER BY batch_key DESC, material_number, question_number LIMIT ?"; args.append(limit)
        with self.connect() as conn:
            rows=conn.execute(q,args).fetchall()
        return [dict(r) for r in rows]

    def add_manual_question(self, vacancy_id: int, question_type: str, material_number: int, question_text: str, options: dict, correct_answer: str, explanation: str, admin_id: int | None = None) -> int:
        snapshot = self.regulation_snapshot(vacancy_id)
        with self.connect() as conn:
            qnrow = conn.execute("SELECT COALESCE(MAX(question_number),0)+1 AS n FROM question_banks WHERE vacancy_id=? AND question_type=? AND material_number=? AND status='active'", (vacancy_id, question_type, material_number)).fetchone()
            qn = int(qnrow["n"])
            cur=conn.execute("INSERT INTO question_banks(vacancy_id, regulation_version_snapshot, batch_key, question_type, material_number, question_number, question_text, options_json, correct_answer, explanation, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)", (vacancy_id, snapshot, f"manual_{now_str().replace(' ','_')}", question_type, material_number, qn, question_text, dumps(options), correct_answer, explanation, now_str(), now_str()))
            qid=int(cur.lastrowid); conn.commit()
        self.change_log(admin_id, "question_added", "question_bank", qid, {}, {"vacancy_id": vacancy_id, "question_type": question_type, "material_number": material_number, "question_text": question_text})
        return qid

    def get_question_bank_row(self, row_id: int) -> dict | None:
        with self.connect() as conn:
            row=conn.execute("SELECT * FROM question_banks WHERE id=?",(row_id,)).fetchone()
        return dict(row) if row else None

    def update_question_bank_row(self, row_id: int, admin_id: int | None = None, **updates: Any) -> None:
        allowed={"question_text","options_json","correct_answer","explanation","status"}; clean={k:v for k,v in updates.items() if k in allowed}
        if not clean: return
        clean["updated_at"]=now_str()
        with self.connect() as conn:
            old=conn.execute("SELECT * FROM question_banks WHERE id=?",(row_id,)).fetchone()
            conn.execute("UPDATE question_banks SET " + ", ".join(f"{k}=?" for k in clean) + " WHERE id=?", [*clean.values(), row_id]); conn.commit()
        self.change_log(admin_id,"question_updated","question_bank",row_id,dict(old) if old else {},clean)

    def recent_change_logs(self, limit: int = 30) -> list[dict]:
        with self.connect() as conn: rows=conn.execute("SELECT * FROM admin_change_logs ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        with self.connect() as conn:
            result = {}
            for status in ["submitted", "ai_rejected", "invited", "accepted", "rejected", "reserve"]:
                row = conn.execute("SELECT COUNT(*) AS c FROM candidates WHERE status=?", (status,)).fetchone()
                result[status] = int(row["c"])
            row = conn.execute("SELECT COUNT(*) AS c FROM employees").fetchone()
            result["employees"] = int(row["c"])
            row = conn.execute("SELECT COUNT(*) AS c FROM final_tests WHERE status='completed'").fetchone()
            result["final_completed"] = int(row["c"])
        return result


db = Database(settings.db_path)
