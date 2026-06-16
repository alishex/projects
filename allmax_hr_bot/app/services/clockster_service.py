from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Any

import aiohttp

from app.config import settings
from app.database import db

logger = logging.getLogger(__name__)


def _norm_name(value: str | None) -> str:
    value = (value or "").lower().strip()
    value = value.replace("'", "").replace("`", "").replace("ʼ", "")
    value = re.sub(r"[^a-zа-яёўқғҳ0-9\s]", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _score_names(a: str | None, b: str | None) -> float:
    na, nb = _norm_name(a), _norm_name(b)
    if not na or not nb:
        return 0.0
    base = SequenceMatcher(None, na, nb).ratio()
    aw, bw = set(na.split()), set(nb.split())
    word_score = len(aw & bw) / max(len(aw | bw), 1)
    # Familya/ism joyi almashib ketganda ham ushlashi uchun ikki signalni qo‘shamiz.
    return round(max(base, (base * 0.65 + word_score * 0.35)), 4)


def _extract_list(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "results", "items", "employees", "users", "people", "records", "attendance", "attendances", "timesheets"):
        value = payload.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        if isinstance(value, dict):
            nested = _extract_list(value)
            if nested:
                return nested
    return []


def _first(obj: dict, keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in obj and obj.get(key) not in (None, ""):
            return obj.get(key)
    return None


def _clockster_employee_id(item: dict) -> str:
    value = _first(item, ("id", "employee_id", "employeeId", "user_id", "userId", "person_id", "personId", "uuid"))
    return str(value or "")


def _clockster_employee_name(item: dict) -> str:
    direct = _first(item, ("full_name", "fullName", "name", "display_name", "displayName", "employee_name", "employeeName"))
    if direct:
        return str(direct)
    first = _first(item, ("first_name", "firstName", "firstname", "given_name")) or ""
    last = _first(item, ("last_name", "lastName", "lastname", "family_name", "surname")) or ""
    middle = _first(item, ("middle_name", "middleName", "patronymic")) or ""
    return " ".join(str(x).strip() for x in (last, first, middle) if str(x).strip())


def _parse_dt(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    # Telegramda o‘qilishi oson bo‘lishi uchun ISO dagi T/Z ni yumshatamiz.
    return text.replace("T", " ").replace("Z", "").split("+")[0]


def _record_date(item: dict, check_in: str | None, check_out: str | None) -> str:
    date_value = _first(item, ("date", "record_date", "recordDate", "day", "work_date", "workDate"))
    if date_value:
        return str(date_value)[:10]
    source = check_in or check_out or datetime.now(settings.tz).strftime("%Y-%m-%d")
    return str(source)[:10]


def normalize_attendance_record(item: dict) -> dict:
    check_in = _parse_dt(_first(item, (
        "check_in", "checkIn", "clock_in", "clockIn", "time_in", "timeIn", "in",
        "start_time", "startTime", "arrival_time", "arrivalTime", "arrived_at", "arrivedAt",
    )))
    check_out = _parse_dt(_first(item, (
        "check_out", "checkOut", "clock_out", "clockOut", "time_out", "timeOut", "out",
        "end_time", "endTime", "leave_time", "leaveTime", "left_at", "leftAt",
    )))
    status = _first(item, ("status", "state", "attendance_status", "attendanceStatus", "type")) or ""
    return {
        "record_date": _record_date(item, check_in, check_out),
        "check_in": check_in,
        "check_out": check_out,
        "status": str(status),
        "late_minutes": int(_first(item, ("late_minutes", "lateMinutes", "late", "delay_minutes", "delayMinutes")) or 0),
        "work_minutes": int(_first(item, ("work_minutes", "workMinutes", "worked_minutes", "workedMinutes", "duration_minutes", "durationMinutes")) or 0),
        "branch": _first(item, ("branch", "branch_name", "branchName", "location", "location_name", "locationName")),
        "raw": item,
    }


class ClocksterClient:
    def __init__(self) -> None:
        self.base = settings.clockster_api_base.rstrip("/") + "/"
        self.headers = {
            "Authorization": f"Bearer {settings.clockster_api_token}",
            "Accept": "application/json",
            "User-Agent": "ALLMAX-HR-Bot/1.0",
        }

    async def _get(self, endpoint: str, params: dict | None = None) -> Any:
        url = self.base + endpoint.strip("/")
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout, headers=self.headers) as session:
            async with session.get(url, params=params or {}) as resp:
                text = await resp.text()
                if resp.status == 401:
                    raise PermissionError("Clockster 401 Unauthorized: token noto‘g‘ri, o‘chirilgan yoki muddati tugagan.")
                if resp.status >= 400:
                    raise RuntimeError(f"Clockster API error {resp.status}: {text[:250]}")
                try:
                    return await resp.json(content_type=None)
                except Exception:
                    raise RuntimeError(f"Clockster JSON qaytarmadi: {text[:250]}")

    async def list_employees(self) -> list[dict]:
        last_error: Exception | None = None
        for endpoint in settings.clockster_employee_paths:
            try:
                payload = await self._get(endpoint)
                items = _extract_list(payload)
                if items:
                    return items
            except Exception as exc:
                last_error = exc
                logger.info("Clockster employees endpoint failed %s: %s", endpoint, exc)
        if last_error:
            raise last_error
        return []

    async def list_attendance(self, clockster_employee_id: str, start_date: str, end_date: str) -> list[dict]:
        params = {
            "employee_id": clockster_employee_id,
            "employeeId": clockster_employee_id,
            "user_id": clockster_employee_id,
            "userId": clockster_employee_id,
            "person_id": clockster_employee_id,
            "from": start_date,
            "to": end_date,
            "date_from": start_date,
            "date_to": end_date,
            "start_date": start_date,
            "end_date": end_date,
        }
        last_error: Exception | None = None
        for endpoint in settings.clockster_attendance_paths:
            try:
                path = endpoint.format(employee_id=clockster_employee_id)
                payload = await self._get(path, params=params)
                items = _extract_list(payload)
                # Ba’zi endpointlar hamma xodimni qaytaradi — ID bo‘yicha filtr qilamiz.
                filtered: list[dict] = []
                for item in items:
                    item_emp = _clockster_employee_id(item) or str(_first(item, ("employee", "user", "person")) or "")
                    if not item_emp or item_emp == clockster_employee_id or clockster_employee_id in str(item):
                        filtered.append(item)
                return [normalize_attendance_record(x) for x in (filtered or items)]
            except Exception as exc:
                last_error = exc
                logger.info("Clockster attendance endpoint failed %s: %s", endpoint, exc)
        if last_error:
            raise last_error
        return []


async def find_clockster_employee_by_name(full_name: str) -> tuple[str, str, float, dict] | None:
    if not settings.clockster_ready:
        return None
    client = ClocksterClient()
    employees = await client.list_employees()
    best: tuple[str, str, float, dict] | None = None
    for item in employees:
        cid = _clockster_employee_id(item)
        cname = _clockster_employee_name(item)
        score = _score_names(full_name, cname)
        if cid and cname and (best is None or score > best[2]):
            best = (cid, cname, score, item)
    if best and best[2] >= settings.clockster_match_threshold:
        return best
    return None


async def sync_employee_attendance(employee_id: int) -> dict:
    employee = db.get_employee(employee_id)
    if not employee:
        return {"ok": False, "message": "Xodim topilmadi."}
    # Clockster nazorati faqat stajirovka yakunlanib, yakuniy 30 talik test tugagandan keyin boshlanadi.
    # Yakuniy test tugamaguncha employees.status='onboarding' bo‘ladi va Clocksterga ulanmaydi.
    if employee.get("status") != "active" or not employee.get("completed_at"):
        return {
            "ok": False,
            "message": "Clockster nazorati yakuniy test tugagandan keyin boshlanadi. Xodim hali stajirovkada.",
        }
    if not settings.clockster_ready:
        return {"ok": False, "message": "Clockster .env sozlamalari yoqilmagan yoki token kiritilmagan."}

    try:
        link = db.get_clockster_link(employee_id)
        if not link:
            matched = await find_clockster_employee_by_name(employee.get("full_name") or "")
            if not matched:
                db.save_clockster_sync_log(employee_id, "not_found", "Clocksterda F.I.SH. bo‘yicha mos xodim topilmadi.", {"full_name": employee.get("full_name")})
                return {"ok": False, "message": "Clocksterda F.I.SH. bo‘yicha mos xodim topilmadi."}
            clockster_id, clockster_name, score, raw = matched
            db.save_clockster_link(employee_id, clockster_id, clockster_name, score, raw)
            link = db.get_clockster_link(employee_id)

        end = datetime.now(settings.tz).date()
        start = end - timedelta(days=max(settings.clockster_lookback_days, 1))
        client = ClocksterClient()
        records = await client.list_attendance(str(link["clockster_employee_id"]), start.isoformat(), end.isoformat())
        saved = db.save_clockster_attendance_records(employee_id, str(link["clockster_employee_id"]), records)
        db.save_clockster_sync_log(employee_id, "ok", f"{saved} ta attendance yozuvi sinxron qilindi.")
        return {"ok": True, "message": f"{saved} ta yozuv sinxron qilindi.", "records": saved}
    except Exception as exc:
        logger.exception("Clockster sync employee failed")
        db.save_clockster_sync_log(employee_id, "error", str(exc))
        return {"ok": False, "message": str(exc)}


async def sync_all_clockster_attendance(limit: int = 100) -> dict:
    if not settings.clockster_ready:
        return {"ok": False, "message": "Clockster .env sozlamalari yoqilmagan yoki token kiritilmagan."}
    employees = db.list_employees(status="active", limit=limit)
    ok = 0
    failed = 0
    messages: list[str] = []
    for employee in employees:
        result = await sync_employee_attendance(int(employee["id"]))
        if result.get("ok"):
            ok += 1
        else:
            failed += 1
            messages.append(f"#{employee['id']} {employee.get('full_name')}: {result.get('message')}")
    return {"ok": failed == 0, "synced": ok, "failed": failed, "messages": messages[:10]}
