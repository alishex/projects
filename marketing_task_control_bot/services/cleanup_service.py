"""Best-effort removal of temporary workflow messages."""
from __future__ import annotations

import logging
from aiogram import Bot

from database.repositories import TemporaryMessageRepository

logger = logging.getLogger(__name__)


class CleanupService:
    def __init__(self, bot: Bot, repository: TemporaryMessageRepository):
        self.bot = bot
        self.repository = repository

    async def remember(self, chat_id: int, message_id: int, workflow_type: str) -> None:
        await self.repository.add(chat_id, message_id, workflow_type)

    async def cleanup(self, chat_id: int, workflow_type: str) -> None:
        rows = await self.repository.pending(chat_id, workflow_type)
        for row in rows:
            try:
                await self.bot.delete_message(row["chat_id"], row["message_id"])
            except Exception:
                logger.info("Vaqtinchalik xabar o‘chirilmadi: chat=%s message=%s", row["chat_id"], row["message_id"])
            finally:
                await self.repository.mark_deleted(row["id"])
