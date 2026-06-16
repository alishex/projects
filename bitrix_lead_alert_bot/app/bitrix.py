from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger(__name__)


class BitrixError(RuntimeError):
    pass


class BitrixClient:
    def __init__(self) -> None:
        base = settings.bitrix_webhook_base_url.strip()
        if base and not base.endswith("/"):
            base += "/"
        self.base_url = base
        self.timeout = settings.request_timeout_seconds

    def _method_url(self, method: str) -> str:
        method = method.strip().removesuffix(".json")
        return f"{self.base_url}{method}.json"

    async def call(self, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.base_url:
            raise BitrixError("BITRIX_WEBHOOK_BASE_URL to'ldirilmagan")

        url = self._method_url(method)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload or {})
            except httpx.HTTPError as exc:
                raise BitrixError(f"Bitrix24 HTTP xatolik: {exc}") from exc

        if response.status_code >= 400:
            raise BitrixError(f"Bitrix24 HTTP {response.status_code}: {response.text[:500]}")

        data = response.json()
        if "error" in data:
            description = data.get("error_description") or data.get("error")
            raise BitrixError(f"Bitrix24 API xatolik: {description}")
        return data

    async def get_lead(self, lead_id: int) -> dict[str, Any]:
        """Get lead using modern universal method first, then legacy fallback."""
        try:
            data = await self.call(
                "crm.item.get",
                {"entityTypeId": settings.bitrix_entity_type_id, "id": lead_id},
            )
            item = data.get("result", {}).get("item")
            if isinstance(item, dict):
                return item
        except Exception as exc:
            logger.warning("crm.item.get failed for lead %s, trying crm.lead.get: %s", lead_id, exc)

        data = await self.call("crm.lead.get", {"id": lead_id})
        result = data.get("result")
        if not isinstance(result, dict):
            raise BitrixError(f"Lead topilmadi yoki noto'g'ri javob: {lead_id}")
        return result

    async def get_contact(self, contact_id: int) -> dict[str, Any]:
        data = await self.call("crm.contact.get", {"id": contact_id})
        result = data.get("result")
        if not isinstance(result, dict):
            raise BitrixError(f"Contact topilmadi yoki noto'g'ri javob: {contact_id}")
        return result

    async def list_recent_leads(self, limit: int = 50) -> list[dict[str, Any]]:
        """List newest leads. Uses universal CRM method, fallback to legacy method."""
        limit = max(1, min(int(limit), 50))
        try:
            data = await self.call(
                "crm.item.list",
                {
                    "entityTypeId": settings.bitrix_entity_type_id,
                    "order": {"id": "DESC"},
                    "select": [
                        "id",
                        "title",
                        "name",
                        "lastName",
                        "phone",
                        "email",
                        "sourceId",
                        "stageId",
                        "assignedById",
                        "contactId",
                        "contactIds",
                        "createdTime",
                        "updatedTime",
                    ],
                    "start": -1,
                },
            )
            items = data.get("result", {}).get("items", [])
            if isinstance(items, list):
                return items[:limit]
        except Exception as exc:
            logger.warning("crm.item.list failed, trying crm.lead.list: %s", exc)

        data = await self.call(
            "crm.lead.list",
            {
                "order": {"ID": "DESC"},
                "filter": {},
                "select": [
                    "ID",
                    "TITLE",
                    "NAME",
                    "LAST_NAME",
                    "PHONE",
                    "EMAIL",
                    "SOURCE_ID",
                    "STATUS_ID",
                    "ASSIGNED_BY_ID",
                    "CONTACT_ID",
                    "DATE_CREATE",
                    "DATE_MODIFY",
                ],
                "start": -1,
            },
        )
        result = data.get("result", [])
        if not isinstance(result, list):
            raise BitrixError("crm.lead.list noto'g'ri javob qaytardi")
        return result[:limit]


bitrix_client = BitrixClient()
