from __future__ import annotations

import html
import json
import re
from datetime import datetime
from typing import Any

from .config import settings
from .telegram_client import mention_html


def _first_not_empty(*values: Any, default: str = "—") -> str:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        if isinstance(value, list) and not value:
            continue
        return str(value).strip()
    return default


def _get(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def extract_lead_id_from_payload(payload: dict[str, Any]) -> int | None:
    """Support Bitrix outgoing webhook formats and manual JSON formats."""
    direct_candidates = [
        payload.get("lead_id"),
        payload.get("leadId"),
        payload.get("ID"),
        payload.get("id"),
        payload.get("data[FIELDS][ID]"),
        payload.get("data[ID]"),
    ]

    data = payload.get("data")
    if isinstance(data, dict):
        fields = data.get("FIELDS") or data.get("fields")
        if isinstance(fields, dict):
            direct_candidates.extend([fields.get("ID"), fields.get("id")])
        direct_candidates.extend([data.get("ID"), data.get("id")])

    fields = payload.get("FIELDS") or payload.get("fields")
    if isinstance(fields, dict):
        direct_candidates.extend([fields.get("ID"), fields.get("id")])

    for candidate in direct_candidates:
        if candidate is None:
            continue
        match = re.search(r"\d+", str(candidate))
        if match:
            return int(match.group(0))

    # Some Bitrix events can include document_id like CRM_LEAD_123.
    for key in ("document_id", "documentId", "entity_id", "entityId"):
        value = payload.get(key)
        if value:
            match = re.search(r"(\d+)$", str(value))
            if match:
                return int(match.group(1))

    return None


def lead_id_from_item(item: dict[str, Any]) -> int | None:
    value = _get(item, "id", "ID")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        match = re.search(r"\d+", str(value))
        return int(match.group(0)) if match else None


def extract_contact_id(lead: dict[str, Any]) -> int | None:
    candidates: list[Any] = [
        _get(lead, "contactId", "CONTACT_ID", "contact_id"),
        _get(lead, "contactIds", "CONTACT_IDS"),
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        if isinstance(candidate, list) and candidate:
            candidate = candidate[0]
        if isinstance(candidate, dict):
            candidate = candidate.get("id") or candidate.get("ID") or candidate.get("value")
        match = re.search(r"\d+", str(candidate))
        if match:
            return int(match.group(0))
    return None


def _extract_multifield(lead: dict[str, Any], *keys: str) -> str:
    value = _get(lead, *keys)
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return _first_not_empty(first.get("VALUE"), first.get("value"))
        return str(first)
    if isinstance(value, dict):
        return _first_not_empty(value.get("VALUE"), value.get("value"))
    return _first_not_empty(value)


def extract_phone(lead: dict[str, Any]) -> str:
    phone = _extract_multifield(lead, "phone", "PHONE", "PHONE_WORK", "phoneWork")
    if phone != "—":
        return phone
    contact = lead.get("_contact")
    if isinstance(contact, dict):
        return _extract_multifield(contact, "PHONE", "phone", "PHONE_WORK", "phoneWork")
    return "—"


def extract_email(lead: dict[str, Any]) -> str:
    email = _extract_multifield(lead, "email", "EMAIL")
    if email != "—":
        return email
    contact = lead.get("_contact")
    if isinstance(contact, dict):
        return _extract_multifield(contact, "EMAIL", "email")
    return "—"


def full_name_from(data: dict[str, Any]) -> str:
    full = _first_not_empty(_get(data, "fullName", "FULL_NAME"), default="")
    if full:
        return full

    name = _first_not_empty(_get(data, "name", "NAME"), default="")
    second = _first_not_empty(_get(data, "secondName", "SECOND_NAME"), default="")
    last = _first_not_empty(_get(data, "lastName", "LAST_NAME"), default="")
    company = _first_not_empty(_get(data, "companyTitle", "COMPANY_TITLE", "companyName", "COMPANY_NAME"), default="")

    parts = [part for part in [name, second, last] if part]
    if parts:
        return " ".join(parts)
    if company:
        return company
    return "—"


def extract_customer_name(lead: dict[str, Any]) -> str:
    lead_name = full_name_from(lead)
    if lead_name != "—":
        return lead_name

    contact = lead.get("_contact")
    if isinstance(contact, dict):
        contact_name = full_name_from(contact)
        if contact_name != "—":
            return contact_name

    return "—"


def format_datetime(value: Any) -> str:
    if not value:
        return "—"
    text = str(value)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return text


def lead_link(lead_id: int) -> str:
    if not settings.bitrix_portal_url:
        return ""
    return f"{settings.bitrix_portal_url}/crm/lead/details/{lead_id}/"


def format_lead_message(lead_id: int, lead: dict[str, Any]) -> str:
    title = _first_not_empty(_get(lead, "title", "TITLE"))
    customer_name = extract_customer_name(lead)
    phone = extract_phone(lead)
    email = extract_email(lead)
    source = _first_not_empty(_get(lead, "sourceId", "SOURCE_ID"))
    stage = _first_not_empty(_get(lead, "stageId", "STATUS_ID"))
    assigned = _first_not_empty(_get(lead, "assignedById", "ASSIGNED_BY_ID"))
    created = format_datetime(_get(lead, "createdTime", "DATE_CREATE", "dateCreate"))
    link = lead_link(lead_id)

    lines = [
        "🆕 <b>Yangi lead tushdi</b>",
        "",
        f"👤 Mas’ul: {mention_html()}",
        f"🆔 Lead ID: <code>{html.escape(str(lead_id))}</code>",
        f"📌 Nomi: <b>{html.escape(title)}</b>",
        f"🙋 Mijoz ismi: {html.escape(customer_name)}",
        f"📞 Telefon: {html.escape(phone)}",
        f"✉️ Email: {html.escape(email)}",
        f"📍 Manba: {html.escape(source)}",
        f"📊 Status: {html.escape(stage)}",
        f"👨‍💼 Bitrix mas’ul ID: {html.escape(assigned)}",
        f"🕒 Vaqt: {html.escape(created)}",
    ]
    if link:
        lines.extend(["", f"🔗 <a href=\"{html.escape(link)}\">Bitrix24’da ochish</a>"])
    return "\n".join(lines)


def compact_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
