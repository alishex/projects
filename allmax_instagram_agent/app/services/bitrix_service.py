from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import Settings
from app.models import ContactInfo, IncomingMessage, TargetInfo
from app.utils.time_utils import format_for_telegram

log = logging.getLogger(__name__)


class BitrixService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base = settings.bitrix_webhook_url.rstrip("/")

    def enabled(self) -> bool:
        return self.settings.bitrix_enable and bool(self.base)

    def _call(self, method: str, params: dict[str, Any]) -> Any:
        if not self.enabled():
            log.info("Bitrix disabled or BITRIX_WEBHOOK_URL is empty; method %s skipped", method)
            return None
        url = f"{self.base}/{method}.json"
        with httpx.Client(timeout=self.settings.bitrix_timeout) as client:
            resp = client.post(url, json=params)
            resp.raise_for_status()
            data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Bitrix error {data.get('error')}: {data.get('error_description')}")
        result = data.get("result")
        log.info("Bitrix method %s completed", method)
        return result

    def resolve_status_id(self, name: str | None, explicit_id: str | None) -> str | None:
        if explicit_id:
            return explicit_id
        if not name:
            return None
        try:
            result = self._call("crm.status.list", {"filter": {"ENTITY_ID": "STATUS"}}) or []
            for item in result:
                if str(item.get("NAME", "")).strip().lower() == name.strip().lower():
                    return item.get("STATUS_ID")
        except Exception as exc:  # noqa: BLE001
            log.warning("Bitrix status resolve failed: %s", exc)
        return None

    def find_duplicate_lead(self, phone: str) -> str | None:
        if not (self.enabled() and self.settings.bitrix_duplicate_check_enable):
            return None
        try:
            result = self._call(
                "crm.duplicate.findbycomm",
                {"entity_type": "LEAD", "type": "PHONE", "values": [phone]},
            )
            leads = ((result or {}).get("LEAD") or []) if isinstance(result, dict) else []
            if leads:
                return str(leads[0])
        except Exception as exc:  # noqa: BLE001
            log.warning("Bitrix duplicate.findbycomm failed; trying crm.lead.list: %s", exc)
        try:
            result = self._call(
                "crm.lead.list",
                {"filter": {"PHONE": phone}, "select": ["ID", "TITLE", "PHONE"]},
            ) or []
            if result:
                return str(result[0].get("ID"))
        except Exception as exc:  # noqa: BLE001
            log.warning("Bitrix crm.lead.list duplicate check failed: %s", exc)
        return None

    def create_lead(self, contact: ContactInfo, msg: IncomingMessage, history_text: str = "") -> str | None:
        if not self.enabled():
            return None
        target = msg.target
        status_id = self.resolve_status_id(
            self.settings.bitrix_target_lead_status_name if target.detected else self.settings.bitrix_lead_status_name,
            self.settings.bitrix_target_lead_status_id if target.detected else self.settings.bitrix_lead_status_id,
        )
        phone = contact.phone or ""
        nick = msg.full_name or (f"@{msg.username.lstrip('@')}" if msg.username else "")
        title_parts = [self.settings.bitrix_lead_title_prefix, contact.name or nick or "Instagram mijoz", phone]
        if self.settings.bitrix_use_instagram_nick_in_title and nick:
            title_parts.insert(1, nick)
        title = " | ".join([p for p in title_parts if p])
        comments = self._build_comments(contact, msg, target)
        fields: dict[str, Any] = {
            "TITLE": title,
            "NAME": contact.name or nick or "Instagram mijoz",
            "PHONE": [{"VALUE": phone, "VALUE_TYPE": "WORK"}],
            "SOURCE_ID": self.settings.bitrix_source_id,
            "SOURCE_DESCRIPTION": self.settings.bitrix_source_description,
            "ASSIGNED_BY_ID": self.settings.bitrix_assigned_by_id,
            "COMMENTS": comments,
        }
        if status_id:
            fields["STATUS_ID"] = status_id
        result = self._call("crm.lead.add", {"fields": fields, "params": {"REGISTER_SONET_EVENT": "Y"}})
        lead_id = str(result) if result is not None else None
        log.info("Bitrix lead created: %s", lead_id)
        return lead_id

    def create_task(self, contact: ContactInfo, msg: IncomingMessage, history_text: str = "", lead_id: str | None = None) -> str | None:
        if not (self.enabled() and self.settings.bitrix_project_enable):
            return None
        target = msg.target
        title_prefix = self.settings.bitrix_target_task_title_prefix if target.detected else self.settings.bitrix_project_task_title_prefix
        stage_id = self.settings.bitrix_target_project_stage_id if target.detected and self.settings.bitrix_target_project_stage_id else self.settings.bitrix_project_stage_id
        description = self._build_task_description(contact, msg, target, lead_id)
        fields: dict[str, Any] = {
            "TITLE": f"{title_prefix} | {contact.name or 'Instagram mijoz'} | {contact.phone or ''}",
            "DESCRIPTION": description,
            "GROUP_ID": self.settings.bitrix_project_group_id,
            "RESPONSIBLE_ID": self.settings.bitrix_project_responsible_id,
        }
        if stage_id:
            fields["STAGE_ID"] = stage_id
        if self.settings.bitrix_project_task_deadline_hours > 0:
            deadline = datetime.now(timezone.utc) + timedelta(hours=self.settings.bitrix_project_task_deadline_hours)
            fields["DEADLINE"] = deadline.isoformat(timespec="seconds")
        if lead_id and self.settings.bitrix_project_bind_to_crm:
            fields["UF_CRM_TASK"] = [f"L_{lead_id}"]
        result = self._call("tasks.task.add", {"fields": fields})
        if isinstance(result, dict):
            task_id = result.get("task", {}).get("id") or result.get("id")
        else:
            task_id = result
        task_id = str(task_id) if task_id else None
        log.info("Bitrix task created: %s", task_id)
        return task_id

    def build_lead_link(self, lead_id: str | None) -> str | None:
        if not lead_id or not self.base:
            return None
        portal = self._portal_root()
        return f"{portal}/crm/lead/details/{lead_id}/" if portal else None

    def build_task_link(self, task_id: str | None) -> str | None:
        if not task_id or not self.base:
            return None
        portal = self._portal_root()
        if not portal:
            return None
        group_id = self.settings.bitrix_project_group_id
        return f"{portal}/workgroups/group/{group_id}/tasks/task/view/{task_id}/"

    def _portal_root(self) -> str | None:
        parsed = urlparse(self.base)
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

    def _build_comments(self, contact: ContactInfo, msg: IncomingMessage, target: TargetInfo) -> str:
        nick = msg.full_name or (f"@{msg.username.lstrip('@')}" if msg.username else "—")
        phone_display = contact.phone or "—"
        lines = [
            "Instagram DM orqali kelgan lead",
            f"Ism: {contact.name or '—'}",
            f"Telefon: {phone_display}",
            f"Instagram nick: {nick}",
            f"Instagram ID: {msg.igsid}",
        ]
        if target.detected:
            lines.append(f"Target/reklama: {target.name}")
        else:
            lines.append("Target/reklama: aniqlanmadi")
        lines.append(f"Yaratilgan vaqt: {format_for_telegram(offset_hours=self.settings.lead_telegram_timezone_offset_hours)}")
        return "\n".join(lines)

    def _build_task_description(self, contact: ContactInfo, msg: IncomingMessage, target: TargetInfo, lead_id: str | None) -> str:
        lead_link = self.build_lead_link(lead_id) or "—"
        nick = msg.full_name or (f"@{msg.username.lstrip('@')}" if msg.username else "—")
        phone_display = contact.phone or "—"
        lines = [
            f"Mijoz ismi: {contact.name or '—'}",
            f"Telefon: {phone_display}",
            f"Instagram nick: {nick}",
            f"Instagram ID: {msg.igsid}",
            f"Bitrix CRM lead: {lead_link}",
        ]
        if target.detected:
            lines.append(f"Target/reklama: {target.name}")
        else:
            lines.append("Target/reklama: aniqlanmadi")
        return "\n".join(lines)
