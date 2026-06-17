import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User

import config
import media_transcriber

logger = logging.getLogger("telegram_ai_assistant.client")

TASHKENT_TZ = timezone(timedelta(hours=5))

MAX_HISTORY_LIMIT = 1000
MAX_MESSAGE_CHARS = 4000


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    """'2026-06-01' yoki to'liq ISO formatdagi sanani UTC datetime'ga aylantiradi."""
    if not value:
        return None
    text = value.strip()
    try:
        if len(text) == 10:
            dt = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=TASHKENT_TZ)
        else:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TASHKENT_TZ)
        return dt.astimezone(timezone.utc)
    except Exception as exc:
        raise ValueError(f"Sana formatini tushunmadim: {value!r} ({exc})")


def _entity_title(entity: Any) -> str:
    if isinstance(entity, User):
        parts = [entity.first_name or "", entity.last_name or ""]
        name = " ".join(p for p in parts if p).strip()
        return name or (f"@{entity.username}" if entity.username else str(entity.id))
    return getattr(entity, "title", None) or str(getattr(entity, "id", ""))


def _entity_type(entity: Any) -> str:
    if isinstance(entity, User):
        return "bot" if entity.bot else "user"
    if isinstance(entity, Channel):
        return "channel" if not entity.megagroup else "group"
    if isinstance(entity, Chat):
        return "group"
    return "unknown"


class TelegramToolset:
    """Foydalanuvchining shaxsiy Telegram akkounti nomidan ishlovchi vositalar to'plami."""

    def __init__(self, client: TelegramClient):
        self.client = client
        self._dialog_cache: list[dict] = []

    async def refresh_dialogs(self, limit: int = 300) -> None:
        dialogs = await self.client.get_dialogs(limit=limit)
        cache = []
        for d in dialogs:
            entity = d.entity
            cache.append(
                {
                    "id": d.id,
                    "title": _entity_title(entity),
                    "type": _entity_type(entity),
                    "username": getattr(entity, "username", None) or "",
                    "unread_count": d.unread_count,
                    "entity": entity,
                }
            )
        self._dialog_cache = cache

    async def list_dialogs(self, query: Optional[str] = None, limit: int = 50) -> list[dict]:
        if not self._dialog_cache:
            await self.refresh_dialogs()
        items = self._dialog_cache
        if query:
            q = query.strip().lower()
            items = [d for d in items if q in d["title"].lower() or q in (d["username"] or "").lower()]
        result = []
        for d in items[:limit]:
            result.append(
                {
                    "id": d["id"],
                    "title": d["title"],
                    "type": d["type"],
                    "username": d["username"],
                    "unread_count": d["unread_count"],
                }
            )
        return result

    async def _resolve_chat(self, chat: Any) -> Any:
        """chat: id (int/str raqam), @username yoki guruh nomi (qisman moslik) bo'lishi mumkin."""
        if isinstance(chat, int):
            return await self.client.get_entity(chat)

        text = str(chat).strip()
        if not text:
            raise ValueError("chat bo'sh bo'lishi mumkin emas")

        if text.lower() in {"me", "self", "saved messages", "saved", "menga"}:
            return await self.client.get_me()

        if text.lstrip("-").isdigit():
            return await self.client.get_entity(int(text))

        if text.startswith("@"):
            return await self.client.get_entity(text)

        if not self._dialog_cache:
            await self.refresh_dialogs()

        lowered = text.lower()
        exact = [d for d in self._dialog_cache if d["title"].lower() == lowered]
        if exact:
            return exact[0]["entity"]

        partial = [d for d in self._dialog_cache if lowered in d["title"].lower()]
        if len(partial) == 1:
            return partial[0]["entity"]
        if len(partial) > 1:
            names = ", ".join(d["title"] for d in partial[:10])
            raise ValueError(
                f"\"{chat}\" nomiga bir nechta chat to'g'ri keladi: {names}. "
                "Aniqroq nom yoki chat ID kiriting."
            )

        raise ValueError(f"\"{chat}\" nomli chat topilmadi. Avval list_dialogs bilan ro'yxatni tekshiring.")

    async def get_chat_history(
        self,
        chat: Any,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 200,
        keyword: Optional[str] = None,
        only_from_me: bool = False,
    ) -> dict:
        entity = await self._resolve_chat(chat)
        limit = max(1, min(limit, MAX_HISTORY_LIMIT))

        start_dt = _parse_date(start_date)
        end_dt = _parse_date(end_date)
        if end_dt:
            end_dt = end_dt + timedelta(days=1)

        keyword_l = keyword.strip().lower() if keyword else None

        messages = []
        scanned = 0
        transcribe_left = config.MAX_TRANSCRIBE_PER_CALL
        async for msg in self.client.iter_messages(entity, limit=MAX_HISTORY_LIMIT, offset_date=end_dt, reverse=False):
            scanned += 1
            if start_dt and msg.date < start_dt:
                break
            if end_dt and msg.date >= end_dt:
                continue
            if only_from_me and not msg.out:
                continue
            text = (msg.message or "").strip()
            if not text:
                kind = media_transcriber.get_media_kind(msg)
                if kind:
                    if transcribe_left > 0:
                        transcribe_left -= 1
                        transcript = await media_transcriber.transcribe_message(self.client, msg)
                        label = media_transcriber.label_for_kind(kind)
                        text = f"[{label}]: {transcript}" if transcript else f"[{label}]"
                    else:
                        text = f"[{media_transcriber.label_for_kind(kind)}, limitga yetildi]"
                elif msg.media:
                    text = "[media]"
                else:
                    continue
            if keyword_l and keyword_l not in text.lower():
                continue
            sender_name = ""
            try:
                sender = await msg.get_sender()
                sender_name = _entity_title(sender) if sender else ""
            except Exception:
                sender_name = ""
            messages.append(
                {
                    "id": msg.id,
                    "date": msg.date.astimezone(TASHKENT_TZ).isoformat(),
                    "sender": sender_name,
                    "is_outgoing": bool(msg.out),
                    "text": text[:MAX_MESSAGE_CHARS],
                }
            )
            if len(messages) >= limit:
                break

        messages.reverse()
        return {
            "chat": _entity_title(entity),
            "count": len(messages),
            "messages": messages,
        }

    async def search_messages(self, chat: Any, query: str, limit: int = 50) -> dict:
        entity = await self._resolve_chat(chat)
        limit = max(1, min(limit, 200))
        results = []
        transcribe_left = config.MAX_TRANSCRIBE_PER_CALL
        async for msg in self.client.iter_messages(entity, search=query, limit=limit):
            text = (msg.message or "").strip()
            if not text:
                kind = media_transcriber.get_media_kind(msg)
                if kind:
                    if transcribe_left > 0:
                        transcribe_left -= 1
                        transcript = await media_transcriber.transcribe_message(self.client, msg)
                        label = media_transcriber.label_for_kind(kind)
                        text = f"[{label}]: {transcript}" if transcript else f"[{label}]"
                    else:
                        text = f"[{media_transcriber.label_for_kind(kind)}, limitga yetildi]"
                elif msg.media:
                    text = "[media]"
            sender_name = ""
            try:
                sender = await msg.get_sender()
                sender_name = _entity_title(sender) if sender else ""
            except Exception:
                pass
            results.append(
                {
                    "id": msg.id,
                    "date": msg.date.astimezone(TASHKENT_TZ).isoformat(),
                    "sender": sender_name,
                    "text": text[:MAX_MESSAGE_CHARS],
                }
            )
        results.reverse()
        return {"chat": _entity_title(entity), "count": len(results), "messages": results}

    async def send_message(self, chat: Any, text: str) -> dict:
        entity = await self._resolve_chat(chat)
        text = text or ""
        sent_ids = []
        for i in range(0, len(text), MAX_MESSAGE_CHARS):
            chunk = text[i : i + MAX_MESSAGE_CHARS]
            msg = await self.client.send_message(entity, chunk)
            sent_ids.append(msg.id)
        return {"chat": _entity_title(entity), "sent_message_ids": sent_ids}

    async def get_chat_info(self, chat: Any) -> dict:
        entity = await self._resolve_chat(chat)
        info = {
            "id": entity.id,
            "title": _entity_title(entity),
            "type": _entity_type(entity),
            "username": getattr(entity, "username", None) or "",
        }
        try:
            full = await self.client.get_participants(entity, limit=0)
            info["participants_count"] = full.total
        except Exception:
            pass
        return info

    @staticmethod
    def get_current_datetime() -> dict:
        now = datetime.now(TASHKENT_TZ)
        return {
            "iso": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "weekday": now.strftime("%A"),
            "timezone": "UTC+5 (Asia/Tashkent)",
        }


async def create_client() -> TelegramClient:
    if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
        raise ValueError("TELEGRAM_API_ID / TELEGRAM_API_HASH .env da topilmadi")
    client = TelegramClient(config.TELEGRAM_SESSION_NAME, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH, receive_updates=False)
    client.parse_mode = "html"
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError(
            "Telegram session topilmadi yoki tasdiqlanmagan. Avval `python login_session.py` ni ishga tushiring."
        )
    return client
