from __future__ import annotations

import base64
import hashlib
import logging
from typing import Any

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
                attachments = message_obj.get("attachments") or []
                # share field (post/reel share without attachments array)
                share = message_obj.get("share") or {}
                if share and not attachments:
                    attachments = [{"type": "share", "payload": share}]
                # story reply
                reply_to = message_obj.get("reply_to") or {}
                story_url = (reply_to.get("story") or {}).get("url") or ""

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
                        attachments=attachments,
                        story_reply_url=story_url,
                    )
                )
            for change in entry.get("changes", []) or []:
                value = change.get("value") or {}
                text = value.get("text") or (value.get("message") or {}).get("text") or ""
                attachments = value.get("attachments") or []
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
                        attachments=attachments,
                    )
                )
        return messages


    def get_user_profile(self, igsid: str) -> dict:
        """Instagram foydalanuvchi profilini API orqali oladi (name, username)."""
        token = self.settings.instagram_access_token
        if not token or token == "replace_me":
            return {}
        try:
            with httpx.Client(timeout=self.settings.http_timeout) as client:
                resp = client.get(
                    f"{self.base_url}/{igsid}",
                    params={"fields": "name,username", "access_token": token},
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:  # noqa: BLE001
            log.debug("Instagram user profile fetch failed for igsid=%s: %s", igsid, exc)
            return {}

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

    def fetch_remote_history(self, igsid: str, limit: int = 20) -> list[dict]:
        """Instagram Graph API dan suhbat tarixini oladi (history bootstrap uchun)."""
        ig_business_id = self.ensure_ig_business_id()
        token = self.settings.instagram_access_token
        if not ig_business_id or not token or token == "replace_me":
            return []
        try:
            with httpx.Client(timeout=self.settings.http_timeout) as client:
                resp = client.get(
                    f"{self.base_url}/{ig_business_id}/conversations",
                    params={
                        "platform": "instagram",
                        "user_id": igsid,
                        "fields": f"messages.limit({limit}){{id,message,from,created_time}}",
                        "access_token": token,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            convs = data.get("data", []) or []
            if not convs:
                return []

            messages_data = (convs[0].get("messages") or {}).get("data", []) or []
            history = []
            for msg in reversed(messages_data):  # eskidan yangiga
                text = (msg.get("message") or "").strip()
                if not text:
                    continue
                from_id = str((msg.get("from") or {}).get("id") or "")
                role = "outgoing" if from_id == str(ig_business_id) else "incoming"
                history.append({"role": role, "text": text})
            log.info("Remote history fetched for igsid=%s: %d messages", igsid, len(history))
            return history
        except Exception as exc:
            log.warning("Remote history fetch failed for igsid=%s: %s", igsid, exc)
            return []

    def process_attachment(self, att: dict) -> tuple[str, list]:
        """
        Attachmentdan matn tavsif va Claude Vision image block larini qaytaradi.
        Returns: (label_text, [claude_content_blocks])
        """
        att_type = (att.get("type") or "").lower()
        payload = att.get("payload") or {}

        if att_type in ("ig_reel", "reel"):
            title = (payload.get("title") or "").strip()
            reel_id = str(payload.get("reel_video_id") or "")
            if not title and reel_id:
                title = self._get_reel_caption(reel_id)
            label = f"[Mijoz Reels ulashdi: {title}]" if title else "[Mijoz Reels ulashdi]"
            return label, []

        elif att_type == "image":
            url = payload.get("url") or ""
            if url:
                b64, mime = self._download_image_b64(url)
                if b64:
                    blocks = [
                        {"type": "text", "text": "[Mijoz rasm yubordi]"},
                        {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                    ]
                    return "[Mijoz rasm yubordi]", blocks
            return "[Mijoz rasm yubordi]", []

        elif att_type == "video":
            title = (payload.get("title") or "").strip()
            return (f"[Mijoz video ulashdi: {title}]" if title else "[Mijoz video yubordi]"), []

        elif att_type == "audio":
            return "[Mijoz audio yubordi]", []

        elif att_type in ("share", "story_share", "ig_share"):
            title = (payload.get("title") or payload.get("description") or "").strip()
            return (f"[Mijoz post ulashdi: {title}]" if title else "[Mijoz post ulashdi]"), []

        elif att_type == "sticker":
            return "[Mijoz stiker yubordi]", []

        elif att_type:
            return f"[{att_type} yuborildi]", []

        return "", []

    def validate_token(self) -> tuple[bool, str]:
        """Token haqiqiy va muddati o'tmagan ekanligini tekshiradi."""
        token = self.settings.instagram_access_token
        if not token or token == "replace_me":
            return False, "Token berilmagan"
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    "https://graph.facebook.com/v20.0/me",
                    params={"fields": "id,name", "access_token": token},
                )
                data = resp.json()
            if "error" in data:
                err = data["error"]
                return False, f"{err.get('type')}: {err.get('message')}"
            return True, f"Token yaroqli: id={data.get('id')} name={data.get('name')}"
        except Exception as exc:
            return False, str(exc)

    def refresh_token(self) -> str | None:
        """Instagram long-lived tokenni yangilaydi (muddati o'tmagan bo'lsa)."""
        token = self.settings.instagram_access_token
        if not token or token == "replace_me":
            return None
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(
                    "https://graph.instagram.com/refresh_access_token",
                    params={"grant_type": "ig_refresh_token", "access_token": token},
                )
                resp.raise_for_status()
                data = resp.json()
            new_token = data.get("access_token")
            expires_in = data.get("expires_in", 0)
            log.info("Token yangilandi, amal qilish muddati: %d kun", expires_in // 86400)
            return new_token
        except Exception as exc:
            log.warning("Token yangilash muvaffaqiyatsiz: %s", exc)
            return None

    def _get_reel_caption(self, reel_id: str) -> str:
        """Reels caption ni Graph API dan oladi."""
        token = self.settings.instagram_access_token
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    f"{self.base_url}/{reel_id}",
                    params={"fields": "caption,description,media_type", "access_token": token},
                )
                data = resp.json()
            return ((data.get("caption") or data.get("description") or "").strip())[:300]
        except Exception as exc:
            log.debug("Reel caption fetch failed for %s: %s", reel_id, exc)
            return ""

    def _download_image_b64(self, url: str) -> tuple[str, str]:
        """URL dan rasmni yuklab base64 va MIME type qaytaradi."""
        try:
            with httpx.Client(timeout=20, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
            mime = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
            if mime not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
                mime = "image/jpeg"
            b64 = base64.standard_b64encode(resp.content).decode()
            return b64, mime
        except Exception as exc:
            log.debug("Image download failed: %s — %s", url[:60], exc)
            return "", "image/jpeg"

    @staticmethod
    def _event_hash(event: dict[str, Any]) -> str:
        return hashlib.sha256(repr(event).encode("utf-8")).hexdigest()
