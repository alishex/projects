from __future__ import annotations

import asyncio
import logging

from app.config import Settings
from app.database import Database
from app.services.instagram_service import InstagramService

log = logging.getLogger(__name__)


async def conversation_sync_loop(settings: Settings, db: Database) -> None:
    if not settings.enable_conversation_sync:
        log.info("Conversation sync worker disabled")
        return
    service = InstagramService(settings)
    log.info("Conversation sync worker started interval=%s", settings.conversation_sync_interval)
    while True:
        try:
            await asyncio.to_thread(service.sync_manual_outgoing, db)
        except asyncio.CancelledError:
            log.info("Conversation sync worker stopped")
            raise
        except Exception as exc:  # noqa: BLE001
            log.warning("Conversation sync worker error: %s", exc)
        await asyncio.sleep(max(10, settings.conversation_sync_interval))
