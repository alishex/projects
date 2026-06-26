from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class ContactInfo:
    name: Optional[str] = None
    phone: Optional[str] = None
    confidence: float = 0.0
    source: str = "none"

    @property
    def is_complete(self) -> bool:
        return bool(self.phone)


@dataclass(slots=True)
class TargetInfo:
    detected: bool = False
    name: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class IncomingMessage:
    event_id: str
    igsid: str
    text: str
    timestamp_ms: Optional[int] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_echo: bool = False
    raw: dict[str, Any] = field(default_factory=dict)
    target: TargetInfo = field(default_factory=TargetInfo)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    story_reply_url: Optional[str] = None


@dataclass(slots=True)
class LeadProcessResult:
    created: bool = False
    duplicate: bool = False
    bitrix_lead_id: Optional[str] = None
    bitrix_task_id: Optional[str] = None
    telegram_sent: bool = False
    reason: Optional[str] = None
