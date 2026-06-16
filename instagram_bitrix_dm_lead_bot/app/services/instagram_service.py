from __future__ import annotations

import hashlib
import logging
from typing import Any, Iterable

import httpx

from app.config import Settings
from app.database import Database
from app.models import IncomingMessage
from app.services.target_detector import detect_target
from app.utils.time_utils import utc_now_iso

log = logging.getLogger(__name__)


class InstagramService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = f"https://graph.facebook.com/{settings.graph_api_version}"

    def ensure_ig_business_id(self) -> str | None:
        if self.settings.meta_ig_business_id and self.settings.meta_ig_business_id != "replace_me":
            return self.settings.meta_ig_business_id
        if not self.settings.meta_page_id or not self.settings.meta_page_access_token:
            return None
        try:
            with httpx.Client(timeout=self.settings.http_timeout) as client:
                resp = client.get(
                    f"{self.base_url}/{self.settings.meta_page_id}",
                    params={"fields": "instagram_business_account", "access_token": self.settings.meta_page_access_token},
                )
                resp.raise_for_status()
                data = resp.json()
            ig_id = (data.get("instagram_business_account") or {}).get("id")
            if ig_id:
                log.info("Resolved Instagram Business ID through Facebook Page")
            return ig_id
        except Exception as exc:  # noqa: BLE001
            log.error("Could not resolve Instagram Business ID: %s", exc)
            return None

    def extract_messages(self, payload: dict[str, Any]) -> list[IncomingMessage]:
        messages: list[IncomingMessage] = []
        target = detect_target(payload, self.settings)
        entries = payload.get("entry", []) or []
        for entry in entries:
            for event in entry.get("messaging", []) or []:
                message_obj = event.get("message") or {}
                text = message_obj.get("text") or event.get("text") or ""
                sender = event.get("sender", {}) or {}
                recipient = event.get("recipient", {}) or {}
                igsid = str(sender.get("id") or event.get("igsid") or "")
                is_echo = bool(message_obj.get("is_echo") or event.get("is_echo"))
                if is_echo and recipient.get("id"):
                    igsid = str(recipient.get("id"))
                if not igsid:
                    continue
                event_id = str(message_obj.get("mid") or event.get("message_id") or self._event_hash(event))
                messages.append(
                    IncomingMessage(
                        event_id=event_id,
                        igsid=igsid,
                        text=text,
                        timestamp_ms=event.get("timestamp"),
                        username=event.get("username") or sender.get("username"),
                        full_name=event.get("full_name") or sender.get("name"),
                        is_echo=is_echo,
                        raw=event,
                        target=target,
                    )
                )
            for change in entry.get("changes", []) or []:
                value = change.get("value") or {}
                text = value.get("text") or (value.get("message") or {}).get("text") or ""
                igsid = str(value.get("sender_id") or value.get("from", {}).get("id") or value.get("igsid") or "")
                if not igsid:
                    continue
                event_id = str(value.get("message_id") or value.get("mid") or self._event_hash(value))
                messages.append(
                    IncomingMessage(
                        event_id=event_id,
                        igsid=igsid,
                        text=text,
                        username=value.get("username"),
                        full_name=value.get("name"),
                        is_echo=bool(value.get("is_echo")),
                        raw=value,
                        target=target,
                    )
                )
        return messages

    def send_message(self, igsid: str, text: str) -> bool:
        ig_business_id = self.ensure_ig_business_id()
        token = self.settings.instagram_access_token
        if not ig_business_id or not token or token == "replace_me":
            log.warning("Instagram credentials are incomplete; message is not sent.")
            return False
        url = f"{self.base_url}/{ig_business_id}/messages"
        payload = {
            "recipient": {"id": igsid},
            "message": {"text": text},
            "messaging_type": "RESPONSE",
        }
        try:
            with httpx.Client(timeout=self.settings.http_timeout) as client:
                resp = client.post(url, params={"access_token": token}, json=payload)
                resp.raise_for_status()
            log.info("Contact template sent to igsid=%s", igsid)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("Instagram send message failed: %s", exc)
            return False

    def sync_manual_outgoing(self, db: Database) -> None:
        ig_business_id = self.ensure_ig_business_id()
        token = self.settings.instagram_access_token
        if not ig_business_id or not token or token == "replace_me":
            return
        try:
            with httpx.Client(timeout=self.settings.http_timeout) as client:
                resp = client.get(
                    f"{self.base_url}/{ig_business_id}/conversations",
                    params={
                        "platform": "instagram",
                        "limit": self.settings.sync_conversation_limit,
                        "fields": f"participants,messages.limit({self.settings.sync_message_limit}){{id,message,from,to,created_time}}",
                        "access_token": token,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            for conv in data.get("data", []) or []:
                participants = conv.get("participants", {}).get("data", []) or []
                customer_id = None
                for p in participants:
                    pid = str(p.get("id") or "")
                    if pid and pid != str(ig_business_id):
                        customer_id = pid
                        break
                if not customer_id:
                    continue
                for msg in (conv.get("messages", {}) or {}).get("data", []) or []:
                    from_id = str((msg.get("from") or {}).get("id") or "")
                    if from_id == str(ig_business_id):
                        db.upsert_conversation(customer_id, manual_outgoing_detected=1)
                        db.append_history(customer_id, "outgoing_sync", msg.get("message") or "", self.settings.max_history_items)
                        log.info("Manual outgoing detected by sync for igsid=%s", customer_id)
                        break
        except Exception as exc:  # noqa: BLE001
            log.warning("Conversation sync failed: %s", exc)

    @staticmethod
    def _event_hash(event: dict[str, Any]) -> str:
        return hashlib.sha256(repr(event).encode("utf-8")).hexdigest()
