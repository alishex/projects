from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Optional

import anthropic

from app.config import Settings
from app.models import ContactInfo
from app.utils.phone import extract_phone, normalize_phone, remove_phone
from app.utils.text import clean_name

log = logging.getLogger(__name__)

NAME_PATTERNS = [
    re.compile(r"(?:ismim|mening ismim|ism|name)\s*[:\-]?\s*([A-Za-zА-Яа-яЁёЎўҚқҒғҲҳ'\- ]{2,40})", re.I),
    re.compile(r"(?:men|man)\s+([A-Za-zА-Яа-яЁёЎўҚқҒғҲҳ'\-]{2,20})", re.I),
]


class ContactParser:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        self.openai_enabled = os.getenv("OPENAI_PARSER_ENABLE", "true").lower() in {
            "1", "true", "yes", "on",
        }

        self.openai_cooldown_seconds = int(os.getenv("OPENAI_COOLDOWN_SECONDS", "900"))
        self._openai_disabled_until = 0.0

    def parse_regex(self, text: str) -> ContactInfo:
        phone = extract_phone(text)
        name: Optional[str] = None

        without_phone = remove_phone(text, phone)

        for pattern in NAME_PATTERNS:
            match = pattern.search(without_phone)
            if match:
                name = clean_name(match.group(1))
                if name:
                    break

        if not name and phone:
            # Har bir qatorni oxiridan tekshirib, birinchi mos kelgan ismni olamiz
            for line in reversed(without_phone.split("\n")):
                candidate = clean_name(line.strip())
                if candidate:
                    name = candidate
                    break

        confidence = 0.85 if phone and name else 0.65 if phone else 0.0
        return ContactInfo(
            name=name,
            phone=phone,
            confidence=confidence,
            source="regex" if phone else "none",
        )

    def parse(self, text: str) -> ContactInfo:
        regex_result = self.parse_regex(text)

        if regex_result.phone:
            return regex_result

        if not self._looks_like_contact_message(text):
            return regex_result

        ai_result = self.parse_openai(text)

        if ai_result and ai_result.phone:
            if not ai_result.name:
                ai_result.name = regex_result.name
            ai_result.source = "claude"
            return ai_result

        return regex_result

    def _looks_like_contact_message(self, text: str) -> bool:
        if not text:
            return False

        lowered = text.lower()
        digits = re.sub(r"\D", "", text)

        keywords = ["tel", "telefon", "raqam", "nomer", "number", "phone", "+998", "998"]

        if any(keyword in lowered for keyword in keywords):
            return True

        return len(digits) >= 9

    def parse_openai(self, text: str) -> Optional[ContactInfo]:
        if not self.openai_enabled:
            log.info("Claude parser disabled by OPENAI_PARSER_ENABLE=false")
            return None

        now = time.time()
        if now < self._openai_disabled_until:
            remaining = int(self._openai_disabled_until - now)
            log.info("Claude parser cooldown active, skipped. remaining_seconds=%s", remaining)
            return None

        api_key = (self.settings.anthropic_api_key or "").strip()
        model = (self.settings.anthropic_model or "").strip()

        if not api_key or api_key == "replace_me":
            return None

        if not model:
            log.warning("Anthropic model is empty. Parser skipped.")
            return None

        system_prompt = (
            "You extract contact info from Instagram DM customer messages.\n"
            "Return ONLY valid JSON with keys: name, phone, confidence.\n\n"
            "Rules:\n"
            "- name: Customer's REAL personal name (e.g. 'Alisher', 'Nodira Karimova'). "
            "ONLY if the customer explicitly stated their name. "
            "Do NOT use: greetings (salom, assalomu alaykum, hi, hello), "
            "system words (incoming, outgoing), product names, or vague phrases. "
            "If no real name is present, use null.\n"
            "- phone: Uzbekistan phone number normalized to +998XXXXXXXXX format. "
            "If not found, use null.\n"
            "- confidence: float 0.0-1.0\n"
            "Return ONLY the JSON object, nothing else."
        )
        user_prompt = "Customer messages:\n" + text[:4000]

        try:
            client = anthropic.Anthropic(api_key=api_key)
            resp = client.messages.create(
                model=model,
                max_tokens=200,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            raw = (resp.content[0].text or "").strip()
            if not raw:
                log.warning("Claude parser returned empty output")
                return None

            parsed = json.loads(raw)

            phone = normalize_phone(parsed.get("phone") or "")
            name = clean_name(parsed.get("name"))
            confidence = float(parsed.get("confidence") or 0.0)

            log.info("Claude parser result: phone_found=%s confidence=%s", bool(phone), confidence)

            return ContactInfo(
                name=name,
                phone=phone,
                confidence=confidence,
                source="claude",
            )

        except anthropic.RateLimitError:
            self._openai_disabled_until = time.time() + self.openai_cooldown_seconds
            log.warning("Claude 429 Rate Limit. Parser paused for %s seconds.", self.openai_cooldown_seconds)
            return None

        except anthropic.APIError as exc:
            log.warning("Claude parser API error: %s", exc)
            return None

        except Exception as exc:
            log.warning("Claude parser failed, regex fallback will be used: %s", exc)
            return None
