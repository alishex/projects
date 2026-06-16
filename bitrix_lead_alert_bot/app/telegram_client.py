from __future__ import annotations

import asyncio
import html
import logging
import time
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger(__name__)


class TelegramError(RuntimeError):
    pass


class TelegramClient:
    def __init__(self) -> None:
        self.token = settings.telegram_bot_token
        self.timeout = settings.request_timeout_seconds
        self._send_lock = asyncio.Lock()
        self._last_send_monotonic = 0.0

    def _url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.token}/{method}"

    async def _respect_min_delay(self) -> None:
        min_delay = max(0.0, float(settings.telegram_min_delay_seconds))
        if min_delay <= 0:
            return
        elapsed = time.monotonic() - self._last_send_monotonic
        wait_for = min_delay - elapsed
        if wait_for > 0:
            await asyncio.sleep(wait_for)

    async def send_message(self, text: str) -> int | None:
        if not self.token:
            raise TelegramError("TELEGRAM_BOT_TOKEN to'ldirilmagan")
        if not settings.telegram_chat_id:
            raise TelegramError("TELEGRAM_CHAT_ID to'ldirilmagan")

        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        async with self._send_lock:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for attempt in range(1, 4):
                    await self._respect_min_delay()
                    try:
                        response = await client.post(self._url("sendMessage"), json=payload)
                    except httpx.HTTPError as exc:
                        raise TelegramError(f"Telegram HTTP xatolik: {exc}") from exc

                    self._last_send_monotonic = time.monotonic()

                    data: dict[str, Any] = response.json()
                    if response.status_code == 429:
                        retry_after = int(data.get("parameters", {}).get("retry_after", 5))
                        logger.warning("Telegram rate limit. retry_after=%s sec", retry_after)
                        await asyncio.sleep(retry_after + 1)
                        continue

                    if response.status_code >= 400 or not data.get("ok"):
                        raise TelegramError(f"Telegram API xatolik: {data}")

                    result = data.get("result", {})
                    message_id = result.get("message_id")
                    logger.info("Telegram xabar yuborildi. message_id=%s", message_id)
                    return int(message_id) if message_id is not None else None

        raise TelegramError("Telegram API xatolik: rate limit qayta urinishlardan keyin ham yechilmadi")


def mention_html() -> str:
    user_id = html.escape(str(settings.telegram_mention_user_id))
    name = html.escape(settings.telegram_mention_name or "Mas'ul")
    return f'<a href="tg://user?id={user_id}">{name}</a>'


telegram_client = TelegramClient()
