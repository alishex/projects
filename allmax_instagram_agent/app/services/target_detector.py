from __future__ import annotations

import json
import logging
from typing import Any

from app.config import Settings
from app.models import TargetInfo

log = logging.getLogger(__name__)

TARGET_KEYS = {"referral", "ad_id", "ad_title", "ad_name", "source", "postback", "metadata", "payload"}


def _walk(obj: Any, found: dict[str, Any]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            lower = str(key).lower()
            if lower in TARGET_KEYS or "ad_" in lower or "ref" in lower:
                found[key] = value
            _walk(value, found)
    elif isinstance(obj, list):
        for item in obj:
            _walk(item, found)


def detect_target(payload: dict[str, Any], settings: Settings) -> TargetInfo:
    if not settings.target_video_detection_enable:
        return TargetInfo(False)
    found: dict[str, Any] = {}
    _walk(payload, found)
    payload_text = json.dumps(payload, ensure_ascii=False).lower()
    keywords = [k.strip().lower() for k in settings.target_video_keywords.split(",") if k.strip()]
    keyword_hit = any(k in payload_text for k in keywords)
    signal_hit = any(key for key in found if str(key).lower() in TARGET_KEYS or "ad_" in str(key).lower())
    if not keyword_hit and not signal_hit:
        return TargetInfo(False)
    name = None
    for key in ("ad_title", "ad_name", "title", "source", "payload"):
        value = found.get(key)
        if isinstance(value, str) and value.strip():
            name = value.strip()[:120]
            break
    name = name or settings.target_video_default_name
    log.info("Target signal detected: %s", name)
    return TargetInfo(True, name, found)
