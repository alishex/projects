from __future__ import annotations

import asyncio
import logging
from typing import Any

from .bitrix import bitrix_client
from .config import settings
from .database import get_db
from .lead_utils import extract_contact_id, format_lead_message
from .telegram_client import telegram_client

logger = logging.getLogger(__name__)


class LeadProcessor:
    def __init__(self) -> None:
        self.db = get_db()
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock_for(self, lead_id: int) -> asyncio.Lock:
        if lead_id not in self._locks:
            self._locks[lead_id] = asyncio.Lock()
        return self._locks[lead_id]

    def is_old_for_realtime_mode(self, lead_id: int, source: str) -> bool:
        """In realtime mode, do not send leads that existed before bot baseline."""
        if not settings.realtime_only_mode:
            return False
        if source == "manual":
            return False
        checkpoint = self.db.get_realtime_checkpoint()
        return checkpoint > 0 and int(lead_id) <= checkpoint and self.db.get_status(lead_id) is None

    async def enqueue_lead(self, lead_id: int, source: str, payload: dict[str, Any] | None = None) -> bool:
        if self.is_old_for_realtime_mode(lead_id, source):
            self.db.mark_skipped(lead_id, f"old_{source}", payload)
            logger.info("Realtime mode: eski lead yuborilmadi: lead_id=%s checkpoint=%s", lead_id, self.db.get_realtime_checkpoint())
            return False

        created = self.db.upsert_pending(lead_id, source, payload)
        if created:
            logger.info("Lead navbatga qo'shildi: lead_id=%s source=%s", lead_id, source)
        else:
            logger.info("Lead allaqachon mavjud: lead_id=%s status=%s", lead_id, self.db.get_status(lead_id))
        return created

    async def enrich_lead(self, lead: dict[str, Any]) -> dict[str, Any]:
        """If lead has linked contact, pull contact to get real customer name/phone/email."""
        contact_id = extract_contact_id(lead)
        if not contact_id:
            return lead
        try:
            contact = await bitrix_client.get_contact(contact_id)
            lead = dict(lead)
            lead["_contact"] = contact
            logger.info("Lead contact bilan boyitildi: contact_id=%s", contact_id)
        except Exception as exc:
            logger.warning("Contact ma'lumotini olishning imkoni bo'lmadi. contact_id=%s error=%s", contact_id, exc)
        return lead

    async def process_lead(self, lead_id: int, source: str = "processor") -> bool:
        async with self._lock_for(lead_id):
            status = self.db.get_status(lead_id)
            if status == "sent":
                logger.info("Lead oldin yuborilgan, o'tkazildi: %s", lead_id)
                return True
            if status == "skipped":
                logger.info("Lead oldin skipped qilingan, o'tkazildi: %s", lead_id)
                return True

            if self.is_old_for_realtime_mode(lead_id, source):
                self.db.mark_skipped(lead_id, f"old_{source}")
                logger.info("Realtime mode: eski lead process qilinmadi: lead_id=%s", lead_id)
                return True

            self.db.upsert_pending(lead_id, source)

            last_error = ""
            lead: dict[str, Any] = {}
            for attempt in range(1, settings.retry_max_attempts + 1):
                try:
                    lead = await bitrix_client.get_lead(lead_id)
                    lead = await self.enrich_lead(lead)
                    text = format_lead_message(lead_id, lead)
                    message_id = await telegram_client.send_message(text)
                    self.db.mark_sent(lead_id, message_id, lead)
                    self.db.set_realtime_checkpoint(lead_id)
                    logger.info("Lead Telegramga yuborildi: lead_id=%s", lead_id)
                    return True
                except Exception as exc:
                    last_error = str(exc)
                    logger.exception(
                        "Lead yuborishda xatolik. lead_id=%s attempt=%s/%s error=%s",
                        lead_id,
                        attempt,
                        settings.retry_max_attempts,
                        last_error,
                    )
                    if attempt < settings.retry_max_attempts:
                        await asyncio.sleep(settings.retry_base_delay_seconds * attempt)

            self.db.mark_failed(lead_id, last_error)
            return False

    async def process_pending(self, limit: int = 100) -> None:
        ids = self.db.pending_lead_ids(limit=limit)
        if not ids:
            return
        logger.info("Pending/failed leadlarni qayta yuborish boshlandi: %s", ids)
        for lead_id in ids:
            await self.process_lead(lead_id, source="retry_pending")


lead_processor = LeadProcessor()
