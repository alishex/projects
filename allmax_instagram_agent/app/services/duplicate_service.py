from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import Settings
from app.database import Database
from app.services.bitrix_service import BitrixService

log = logging.getLogger(__name__)


@dataclass(slots=True)
class DuplicateResult:
    duplicate: bool
    reason: str = ""
    bitrix_lead_id: str | None = None


class DuplicateService:
    def __init__(self, settings: Settings, db: Database, bitrix: BitrixService) -> None:
        self.settings = settings
        self.db = db
        self.bitrix = bitrix

    def check(self, phone: str, igsid: str) -> DuplicateResult:
        if not phone:
            return DuplicateResult(False)
        if self.db.phone_seen_locally(phone):
            log.info("Duplicate phone found in local SQLite: %s", phone)
            return DuplicateResult(True, "local_sqlite")
        if self.settings.bitrix_duplicate_check_enable:
            lead_id = self.bitrix.find_duplicate_lead(phone)
            if lead_id:
                log.info("Duplicate phone found in Bitrix lead ID=%s", lead_id)
                return DuplicateResult(True, "bitrix", lead_id)
        return DuplicateResult(False)
