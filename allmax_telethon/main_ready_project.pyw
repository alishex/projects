import os
import re
import asyncio
import logging
import time
import sqlite3 as _sqlite3
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, SessionPasswordNeededError
import anthropic
import json
from community_agent import CommunityAgent, AgentResult
import moysklad
from media_handler import (
    get_media_kind, transcribe_message, encode_image_for_claude,
    encode_gif_for_claude, encode_sticker_for_claude, prewarm_whisper,
)

# =========================
# ANALYTICS LOGGING
# =========================
_ANALYTICS_DB = Path(__file__).parent / "analytics" / "telegram_dm_log.sqlite3"

_REPORT_TZ = timedelta(hours=5)  # UTC+5 Toshkent

def _init_analytics_db():
    _ANALYTICS_DB.parent.mkdir(exist_ok=True)
    con = _sqlite3.connect(_ANALYTICS_DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS dm_events (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ts    TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS daily_contacts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            date         TEXT NOT NULL,
            user_id      INTEGER NOT NULL,
            display_name TEXT,
            username     TEXT,
            topic        TEXT,
            contact_type TEXT NOT NULL DEFAULT 'general',
            updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(date, user_id)
        )
    """)
    con.commit()
    con.close()


def _save_daily_contact(user_id: int, display_name: str, username: str, topic: str, contact_type: str = "general"):
    today = (datetime.now(timezone.utc) + _REPORT_TZ).strftime("%Y-%m-%d")
    try:
        con = _sqlite3.connect(_ANALYTICS_DB)
        con.execute("""
            INSERT INTO daily_contacts (date, user_id, display_name, username, topic, contact_type, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(date, user_id) DO UPDATE SET
                display_name = excluded.display_name,
                username     = excluded.username,
                topic        = excluded.topic,
                contact_type = CASE
                    WHEN excluded.contact_type = 'order' THEN 'order'
                    WHEN excluded.contact_type = 'human' AND daily_contacts.contact_type != 'order' THEN 'human'
                    ELSE daily_contacts.contact_type
                END,
                updated_at = excluded.updated_at
        """, (today, user_id, display_name, username, topic, contact_type))
        con.commit()
        con.close()
    except Exception as e:
        logging.warning("daily_contact save xatosi: %s", e)

def _log_dm_event(user_id: int):
    try:
        con = _sqlite3.connect(_ANALYTICS_DB)
        con.execute("INSERT INTO dm_events (user_id, ts) VALUES (?, datetime('now'))", (user_id,))
        con.commit()
        con.close()
    except Exception as exc:
        logging.warning("Analytics log xatosi: %s", exc)

load_dotenv()

# =========================
# CONFIG
# =========================
API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "")
SESSION_NAME = os.getenv("SESSION_NAME", "allmax_cm_session")

MIN_REPLY_INTERVAL = float(os.getenv("MIN_REPLY_INTERVAL", "0.8"))
MESSAGE_BURST_WINDOW = float(os.getenv("MESSAGE_BURST_WINDOW", "1.8"))
MAX_BURST_MESSAGES = int(os.getenv("MAX_BURST_MESSAGES", "5"))
ONLY_TEXT_MESSAGES = os.getenv("ONLY_TEXT_MESSAGES", "false").lower() == "true"
COMMUNITY_AGENT_ENABLE = os.getenv("COMMUNITY_AGENT_ENABLE", "false").lower() == "true"

LEAD_GROUP = os.getenv("LEAD_GROUP", "").strip()

BITRIX_ENABLE = os.getenv("BITRIX_ENABLE", "true").lower() == "true"
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "").rstrip("/")
BITRIX_ASSIGNED_BY_ID = int(os.getenv("BITRIX_ASSIGNED_BY_ID", "1"))
BITRIX_LEAD_TITLE_PREFIX = os.getenv("BITRIX_LEAD_TITLE_PREFIX", "TELEGRAM")
BITRIX_SOURCE_ID = os.getenv("BITRIX_SOURCE_ID", "TELEGRAM").strip()
BITRIX_SOURCE_NAME = os.getenv("BITRIX_SOURCE_NAME", "Telegram").strip()
BITRIX_LEAD_STATUS_ID = os.getenv("BITRIX_LEAD_STATUS_ID", "TELEGRAM").strip()
BITRIX_LEAD_STATUS_NAME = os.getenv("BITRIX_LEAD_STATUS_NAME", "Telegram").strip()
BITRIX_FORCE_TELEGRAM_IN_TITLE = os.getenv("BITRIX_FORCE_TELEGRAM_IN_TITLE", "true").lower() == "true"
BITRIX_SOURCE_DESCRIPTION = os.getenv("BITRIX_SOURCE_DESCRIPTION", "Telegram DM orqali kelgan lead")
BITRIX_TIMEOUT = int(os.getenv("BITRIX_TIMEOUT", "20"))

# =========================
# BITRIX24 PROJECT / TASKS CONFIG
# =========================
# CRM lead yaratishdan tashqari, Bitrix24 > Zadachi i Proyekti ichidagi
# aniq projectga avtomatik TASK ochish uchun ishlatiladi.
BITRIX_PROJECT_ENABLE = os.getenv("BITRIX_PROJECT_ENABLE", "false").lower() == "true"
BITRIX_PROJECT_GROUP_ID = int(os.getenv("BITRIX_PROJECT_GROUP_ID", "0") or "0")
BITRIX_PROJECT_RESPONSIBLE_ID = int(
    os.getenv("BITRIX_PROJECT_RESPONSIBLE_ID", str(BITRIX_ASSIGNED_BY_ID)) or str(BITRIX_ASSIGNED_BY_ID)
)
BITRIX_PROJECT_STAGE_ID = int(os.getenv("BITRIX_PROJECT_STAGE_ID", "0") or "0")
BITRIX_PROJECT_TASK_TITLE_PREFIX = os.getenv("BITRIX_PROJECT_TASK_TITLE_PREFIX", "Telegram lead").strip()
BITRIX_PROJECT_TASK_DEADLINE_HOURS = int(os.getenv("BITRIX_PROJECT_TASK_DEADLINE_HOURS", "0") or "0")
BITRIX_PROJECT_BIND_TO_CRM = os.getenv("BITRIX_PROJECT_BIND_TO_CRM", "true").lower() == "true"

NEW_CHAT_CONTACT_TEMPLATE = (
    "Murojaatingiz qabul qilindi. Batafsil ma’lumot berishimiz uchun ism va raqamingizni yozib qoldiring. +998-78-555-31-31 raqamidan sizga bog‘lanamiz."
)

if not API_ID or not API_HASH:
    raise ValueError("TELEGRAM_API_ID yoki TELEGRAM_API_HASH topilmadi.")

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# =========================
# CLIENTS / STATE
# =========================
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
community_agent_inst = (
    CommunityAgent(ANTHROPIC_API_KEY, ANTHROPIC_MODEL)
    if COMMUNITY_AGENT_ENABLE and ANTHROPIC_API_KEY
    else None
)
last_reply_time = defaultdict(lambda: 0.0)
user_queues = {}
user_workers = {}
resolved_entities = {"lead_group": None}

lead_state = defaultdict(lambda: {
    "name": "",
    "phone": "",
    "asked": False,
    "sent_to_group": False,
    "sent_to_bitrix": False,
    "bitrix_lead_id": None,
    "sent_to_project_task": False,
    "bitrix_task_id": None,
})

# =========================
# HELPERS
# =========================
def normalize_template_text(text: str) -> str:
    cleaned = (text or "").strip().lower()
    cleaned = cleaned.replace("’", "'").replace("‘", "'").replace("`", "'")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def split_text_into_chunks(text: str, max_length: int = 3500) -> list[str]:
    if not text:
        return []

    text = text.strip()
    if len(text) <= max_length:
        return [text]

    chunks = []
    remaining = text

    while len(remaining) > max_length:
        cut = remaining.rfind("\n\n", 0, max_length)
        if cut == -1:
            cut = remaining.rfind("\n", 0, max_length)
        if cut == -1:
            cut = remaining.rfind(". ", 0, max_length)
        if cut == -1:
            cut = remaining.rfind(" ", 0, max_length)
        if cut == -1:
            cut = max_length

        chunk = remaining[:cut].strip()
        if chunk:
            chunks.append(chunk)

        remaining = remaining[cut:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks


async def send_long_message(event, text: str, reply_to_message_id: Optional[int] = None):
    chunks = split_text_into_chunks(text, max_length=3500)
    if not chunks:
        return

    first_reply_to = reply_to_message_id or event.id
    for chunk in chunks:
        await event.client.send_message(event.chat_id, chunk, reply_to=first_reply_to)
        await asyncio.sleep(0.25)


async def small_typing_delay(text: str):
    delay = min(2.2, max(0.4, len(text) * 0.01))
    await asyncio.sleep(delay)


def parse_peer_value(value: str):
    value = (value or "").strip()
    if not value:
        return None

    if value.startswith("@") or value.startswith("https://") or value.startswith("http://") or value.startswith("t.me/"):
        return value

    try:
        return int(value)
    except ValueError:
        return value


async def resolve_target_entity(raw_value: str, cache_key: str):
    if resolved_entities.get(cache_key) is not None:
        return resolved_entities[cache_key]

    target = parse_peer_value(raw_value)
    if target is None:
        raise ValueError(f"{cache_key} uchun qiymat berilmagan")

    entity = await client.get_entity(target)
    resolved_entities[cache_key] = entity
    logging.info("Resolved %s successfully: %s", cache_key, raw_value)
    return entity


# =========================
# CLAUDE CONTACT PARSING
# =========================
def parse_first_json_object(text: str) -> dict:
    if not text:
        return {}

    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return {}

    try:
        return json.loads(match.group(0))
    except Exception:
        return {}


def ask_openai_contact_parser(text: str) -> tuple[str, str]:
    if not anthropic_client or not text.strip():
        return "", ""

    system_prompt = (
        "Sen Telegram DM uchun faqat kontakt aniqlovchi analizatorsan. "
        "Senga kelgan matndan faqat mijozning ISMI va TELEFON raqami bor-yo'qligini aniqlaysan. "
        "Hech qachon taxmin qilma, o'zingdan ma'lumot to'qima. "
        "Salomlashuv, yordam so'rovi, savdo savoli yoki oddiy gaplarni ism deb qabul qilma. "
        "Telefon faqat aniq ko'rsatilgan raqam bo'lsa olinadi. "
        "Uzbek telefon formatlarini tushun: +998XXXXXXXXX, 998XXXXXXXXX yoki 9 xonali lokal raqam. "
        "Ism bo'lsa 1-3 so'zli real odam ismi bo'lsin. "
        "Javobing faqat JSON bo'lsin: {\"name\":\"\",\"phone\":\"\"}. Boshqa matn yozma."
    )
    user_prompt = f"Matn:\n{text}"

    try:
        response = anthropic_client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=256,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = (response.content[0].text or "{}").strip()
        data = parse_first_json_object(raw)
        name = str(data.get("name") or "").strip()
        phone = str(data.get("phone") or "").strip()
        return name, phone
    except anthropic.RateLimitError as e:
        logging.warning("Claude contact parser rate limit: %s", e)
        return "", ""
    except anthropic.APIError as e:
        logging.warning("Claude contact parser API error: %s", e)
        return "", ""
    except Exception as e:
        logging.exception("Claude contact parser error: %s", e)
        return "", ""


# =========================
# CONTACT PARSING
# =========================
def normalize_phone(text: str) -> str:
    if not text:
        return ""

    s = text.strip()
    s = s.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    s = s.replace(".", "").replace("_", "")
    digits = re.sub(r"\D", "", s)

    if s.startswith("+998") and len(re.sub(r"\D", "", s)) == 12:
        return f"+{digits}"

    if digits.startswith("998") and len(digits) == 12:
        return f"+{digits}"

    if len(digits) == 9:
        return f"+998{digits}"

    m = re.search(r"(\+?998[\s\-\(\)]*\d{2}[\s\-\(\)]*\d{3}[\s\-\(\)]*\d{2}[\s\-\(\)]*\d{2})", text)
    if m:
        candidate = re.sub(r"\D", "", m.group(1))
        if len(candidate) == 12 and candidate.startswith("998"):
            return f"+{candidate}"

    return ""


def looks_like_name(text: str) -> bool:
    if not text:
        return False

    cleaned = re.sub(r"\s+", " ", text.strip())
    lowered = cleaned.lower()

    if len(cleaned) < 2 or len(cleaned) > 40:
        return False
    if any(ch.isdigit() for ch in cleaned):
        return False

    words = [w for w in re.split(r"\s+", lowered) if w]
    if not (1 <= len(words) <= 3):
        return False

    bad_words = {
        "salom", "assalomu", "alaykum", "va", "rahmat", "aka", "opa", "uka",
        "man", "manda", "manga", "menga", "mengayam", "bizga", "biz", "ha", "yoq", "yo‘q",
        "kerak", "yordam", "yordamiz", "bor", "bormi", "qancha", "narx", "razmer",
        "rang", "manzil", "dastavka", "zakaz", "buyurtma", "olmoqchi", "olaman",
        "yozaman", "gaplashamiz", "telefon", "raqam", "nomer", "ism", "familya"
    }
    bad_phrases = {
        "assalomu alaykum", "salom alaykum", "aka manga yordam kerak edi",
        "aka manga yordamiz kerak edi", "manga yordam kerak", "menga yordam kerak"
    }

    if lowered in bad_phrases:
        return False
    if any(word in bad_words for word in words):
        return False

    for word in words:
        if not re.fullmatch(r"[a-zа-яёўқғҳʼ'`’-]+", word, flags=re.I):
            return False

    return True


def extract_name_and_phone_regex(text: str) -> tuple[str, str]:
    if not text:
        return "", ""

    phone = normalize_phone(text)
    name = ""

    explicit_patterns = [
        r"(?:ismim|ismi|mening ismim|my name is|name)\s*[:\-]?\s*([A-Za-zА-Яа-яЁёЎўҚқҒғҲҳʼ'`’\-\s]{2,40})",
    ]

    for pattern in explicit_patterns:
        m = re.search(pattern, text, flags=re.I | re.M)
        if m:
            candidate = re.sub(r"\s+", " ", m.group(1).strip(" ,;:-"))
            if looks_like_name(candidate):
                name = candidate
                break

    if phone and not name:
        fragments = [frag.strip() for frag in re.split(r"[,;\n]", text) if frag.strip()]
        for frag in fragments:
            if normalize_phone(frag):
                continue
            candidate = re.sub(
                r"(ismim|ismi|mening ismim|my name is|name|men)\s*[:\-]?\s*",
                "",
                frag,
                flags=re.I,
            ).strip()
            candidate = re.sub(r"\s+", " ", candidate)
            if looks_like_name(candidate):
                name = candidate
                break

    if not phone and not name:
        candidate = re.sub(r"\s+", " ", text.strip(" ,;:-"))
        if looks_like_name(candidate):
            name = candidate

    return name, phone


def extract_name_and_phone(text: str) -> tuple[str, str]:
    regex_name, regex_phone = extract_name_and_phone_regex(text)

    ai_name = ""
    ai_phone = ""
    if text and text.strip() and anthropic_client:
        ai_name, ai_phone = ask_openai_contact_parser(text)

    final_phone = normalize_phone(ai_phone) or regex_phone

    final_name = ""
    ai_name = re.sub(r"\s+", " ", (ai_name or "").strip(" ,;:-"))
    regex_name = re.sub(r"\s+", " ", (regex_name or "").strip(" ,;:-"))

    if ai_name and looks_like_name(ai_name):
        final_name = ai_name
    elif regex_name and looks_like_name(regex_name):
        final_name = regex_name

    return final_name, final_phone


# =========================
# CHAT HISTORY
# =========================
async def inspect_chat_history(chat_id: int, my_id: int, exclude_message_ids: Optional[set[int]] = None, limit: int = 80) -> dict:
    exclude_message_ids = exclude_message_ids or set()

    history = {
        "prior_total": 0,
        "prior_incoming": 0,
        "prior_outgoing": 0,
        "template_sent_before": False,
        "first_message_from_me": False,
        "last_message_from_me": False,
        "last_message_is_template": False,
        "manual_outgoing_before_contact": False,
    }

    template_norm = normalize_template_text(NEW_CHAT_CONTACT_TEMPLATE)
    kept_messages = []

    async for msg in client.iter_messages(chat_id, limit=limit):
        if msg.id in exclude_message_ids:
            continue
        if getattr(msg, "action", None) is not None:
            continue

        kept_messages.append(msg)
        history["prior_total"] += 1

        if msg.sender_id == my_id:
            history["prior_outgoing"] += 1
            msg_text = (msg.raw_text or "").strip()
            is_template = bool(msg_text and normalize_template_text(msg_text) == template_norm)
            if is_template:
                history["template_sent_before"] = True
            else:
                history["manual_outgoing_before_contact"] = True
        else:
            history["prior_incoming"] += 1

    if kept_messages:
        newest_msg = kept_messages[0]
        oldest_msg = kept_messages[-1]
        history["last_message_from_me"] = newest_msg.sender_id == my_id
        last_text = (newest_msg.raw_text or "").strip()
        history["last_message_is_template"] = bool(
            newest_msg.sender_id == my_id and last_text and normalize_template_text(last_text) == template_norm
        )
        history["first_message_from_me"] = oldest_msg.sender_id == my_id

    history["is_new_inbound_chat"] = history["prior_total"] == 0
    history["started_by_me"] = history["first_message_from_me"]
    return history


async def collect_recent_customer_messages(chat_id: int, my_id: int, exclude_message_ids: Optional[set[int]] = None, limit: int = 20) -> str:
    exclude_message_ids = exclude_message_ids or set()
    parts = []

    async for msg in client.iter_messages(chat_id, limit=limit):
        if msg.id in exclude_message_ids:
            continue
        if getattr(msg, "action", None) is not None:
            continue
        if msg.sender_id == my_id:
            continue

        msg_text = (msg.raw_text or "").strip()
        if not msg_text:
            continue

        parts.append(msg_text)

    if not parts:
        return ""

    parts.reverse()
    return "\n".join(parts)


# =========================
# BITRIX24 HELPERS
# =========================
def bitrix_method_url(method_name: str) -> str:
    if not BITRIX_WEBHOOK_URL:
        raise ValueError("BITRIX_WEBHOOK_URL .env ichida topilmadi.")
    return f"{BITRIX_WEBHOOK_URL}/{method_name}.json"


def bitrix_post(method_name: str, payload: dict) -> dict:
    url = bitrix_method_url(method_name)
    resp = requests.post(url, json=payload, timeout=BITRIX_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Bitrix24 error [{data.get('error')}]: {data.get('error_description')}")
    return data


_bitrix_status_cache: dict[str, list[dict]] = {}


def normalize_bitrix_lookup(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def bitrix_status_list(entity_id: str) -> list[dict]:
    """
    ENTITY_ID='STATUS'  -> lead status/stage list
    ENTITY_ID='SOURCE'  -> lead source list

    Bitrix'da ko‘p hollarda ko‘rinadigan nom "Telegram" bo‘ladi,
    lekin ichki ID "TELEGRAM" yoki "UC_..." bo‘lishi mumkin.
    Shu funksiya ID'ni avtomatik topishga yordam beradi.
    """
    if entity_id in _bitrix_status_cache:
        return _bitrix_status_cache[entity_id]

    data = bitrix_post("crm.status.list", {"filter": {"ENTITY_ID": entity_id}})
    result = data.get("result", []) or []
    _bitrix_status_cache[entity_id] = result
    return result


def resolve_bitrix_status_id(entity_id: str, preferred_id: str, preferred_name: str) -> str:
    """
    Avval .env ichidagi ID bo‘yicha, keyin ko‘rinadigan nom bo‘yicha qidiradi.
    Topilmasa preferred_id qaytariladi. Masalan: TELEGRAM.
    """
    preferred_id = (preferred_id or "").strip()
    preferred_name = (preferred_name or "").strip()

    try:
        items = bitrix_status_list(entity_id)
    except Exception as e:
        logging.warning(
            "Bitrix %s ro‘yxatini o‘qib bo‘lmadi, .env dagi qiymat ishlatiladi: %s",
            entity_id,
            e,
        )
        return preferred_id

    if preferred_id:
        target = normalize_bitrix_lookup(preferred_id)
        for item in items:
            status_id = str(item.get("STATUS_ID", ""))
            if normalize_bitrix_lookup(status_id) == target:
                return status_id

    if preferred_name:
        target = normalize_bitrix_lookup(preferred_name)
        for item in items:
            name = str(item.get("NAME", ""))
            if normalize_bitrix_lookup(name) == target:
                return str(item.get("STATUS_ID", preferred_id))

    return preferred_id


def build_bitrix_title(title_name: str) -> str:
    prefix = (BITRIX_LEAD_TITLE_PREFIX or "TELEGRAM").strip()
    title = f"{prefix} - {title_name}" if prefix else title_name

    # Bitrix ichidagi oddiy qidiruvda ham "Telegram" deb chiqishi uchun
    # lead TITLE ichida Telegram so‘zi bo‘lishini kafolatlaymiz.
    if BITRIX_FORCE_TELEGRAM_IN_TITLE and "telegram" not in title.lower():
        title = f"TELEGRAM - {title}"

    return title


def find_bitrix_duplicates_by_phone(phone: str) -> dict:
    payload = {"type": "PHONE", "values": [phone]}
    data = bitrix_post("crm.duplicate.findbycomm", payload)
    return data.get("result", {}) or {}


def create_bitrix_lead(name: str, phone: str, source_text: str, sender_name: str, username: str, user_id: int) -> Optional[int]:
    title_name = name or "Telegram mijoz"
    source_id = resolve_bitrix_status_id("SOURCE", BITRIX_SOURCE_ID, BITRIX_SOURCE_NAME)
    lead_status_id = resolve_bitrix_status_id("STATUS", BITRIX_LEAD_STATUS_ID, BITRIX_LEAD_STATUS_NAME)

    comments = (
        f"Telegram lead\n"
        f"Ism: {name or '-'}\n"
        f"Telefon: {phone}\n"
        f"Telegram name: {sender_name}\n"
        f"Username: @{username if username else 'yoq'}\n"
        f"Telegram user id: {user_id}\n"
        f"Bitrix source: {source_id}\n"
        f"Bitrix status/stage: {lead_status_id}\n\n"
        f"So‘nggi xabar:\n{source_text}"
    )

    fields = {
        "TITLE": build_bitrix_title(title_name),
        "NAME": name or "",
        "PHONE": [{"VALUE": phone, "VALUE_TYPE": "WORK"}],
        "COMMENTS": comments,
        "SOURCE_ID": source_id,
        "SOURCE_DESCRIPTION": BITRIX_SOURCE_DESCRIPTION,
        "STATUS_ID": lead_status_id,
        "ASSIGNED_BY_ID": BITRIX_ASSIGNED_BY_ID,
        "OPENED": "Y",
    }

    data = bitrix_post("crm.lead.add", {"fields": fields})
    result = data.get("result")
    try:
        return int(result)
    except Exception:
        return None


def push_lead_to_bitrix_if_needed(user_id: int, sender_name: str, username: str, customer_name: str, phone: str, source_text: str) -> tuple[bool, Optional[int], str]:
    state = lead_state[user_id]

    if not BITRIX_ENABLE:
        return False, None, "bitrix_disabled"
    if state["sent_to_bitrix"]:
        return True, state.get("bitrix_lead_id"), "already_sent"
    if not BITRIX_WEBHOOK_URL:
        logging.warning("BITRIX_WEBHOOK_URL berilmagan. Bitrix ga yozilmadi.")
        return False, None, "missing_webhook"

    duplicates = find_bitrix_duplicates_by_phone(phone)
    dup_leads = duplicates.get("LEAD", []) or []
    dup_contacts = duplicates.get("CONTACT", []) or []
    dup_companies = duplicates.get("COMPANY", []) or []

    if dup_leads or dup_contacts or dup_companies:
        existing_id = None
        if dup_leads:
            existing_id = dup_leads[0]
        elif dup_contacts:
            existing_id = dup_contacts[0]
        elif dup_companies:
            existing_id = dup_companies[0]

        # Dublikat topilsa yangi lead ochmaymiz. Lekin logda aniq ko‘rinishi uchun
        # status qaytariladi. Agar mavjud leadni ham Telegram stage'ga ko‘chirish kerak
        # bo‘lsa, buni alohida crm.lead.update orqali yoqish mumkin.
        state["sent_to_bitrix"] = True
        state["bitrix_lead_id"] = existing_id
        return True, existing_id, "duplicate_found_no_new_lead"

    lead_id = create_bitrix_lead(
        name=customer_name,
        phone=phone,
        source_text=source_text,
        sender_name=sender_name,
        username=username,
        user_id=user_id,
    )

    state["sent_to_bitrix"] = True
    state["bitrix_lead_id"] = lead_id
    return True, lead_id, "created"


def extract_bitrix_task_id(data: dict) -> Optional[int]:
    """tasks.task.add javobidan task ID ni xavfsiz ajratib oladi."""
    result = data.get("result")

    if isinstance(result, int):
        return result

    if isinstance(result, str) and result.isdigit():
        return int(result)

    if isinstance(result, dict):
        task = result.get("task") or result
        if isinstance(task, dict):
            task_id = task.get("id") or task.get("ID")
            try:
                return int(task_id)
            except Exception:
                return None

    return None


def build_project_task_title(customer_name: str, phone: str) -> str:
    prefix = (BITRIX_PROJECT_TASK_TITLE_PREFIX or "Telegram lead").strip()
    title_name = customer_name or phone or "Telegram mijoz"
    return f"{prefix} - {title_name}" if prefix else title_name


def build_project_task_description(
    customer_name: str,
    phone: str,
    source_text: str,
    sender_name: str,
    username: str,
    user_id: int,
    bitrix_lead_id: Optional[int] = None,
) -> str:
    telegram_profile = f"https://t.me/{username}" if username else "Username yo‘q"
    lead_line = f"Bitrix CRM lead ID: {bitrix_lead_id}" if bitrix_lead_id else "Bitrix CRM lead ID: yo‘q / CRM o‘chirilgan / dublikat topilmagan"

    return (
        "Telegram orqali kelgan murojaat asosida avtomatik ochilgan task.\n\n"
        f"Ism: {customer_name or '-'}\n"
        f"Telefon: {phone}\n"
        f"Telegram name: {sender_name}\n"
        f"Username: @{username if username else 'yoq'}\n"
        f"Telegram profile: {telegram_profile}\n"
        f"Telegram user id: {user_id}\n"
        f"{lead_line}\n\n"
        f"Mijoz xabari:\n{source_text}"
    )


def create_bitrix_project_task(
    customer_name: str,
    phone: str,
    source_text: str,
    sender_name: str,
    username: str,
    user_id: int,
    bitrix_lead_id: Optional[int] = None,
) -> Optional[int]:
    """
    Bitrix24 > Zadachi i Proyekti ichidagi projectga task ochadi.
    Kerakli .env qiymatlar:
      BITRIX_PROJECT_ENABLE=true
      BITRIX_PROJECT_GROUP_ID=project_id
      BITRIX_PROJECT_RESPONSIBLE_ID=user_id
    """
    if not BITRIX_PROJECT_GROUP_ID:
        raise ValueError("BITRIX_PROJECT_GROUP_ID .env ichida berilmagan. Project ID ni yozing.")

    fields = {
        "TITLE": build_project_task_title(customer_name, phone),
        "DESCRIPTION": build_project_task_description(
            customer_name=customer_name,
            phone=phone,
            source_text=source_text,
            sender_name=sender_name,
            username=username,
            user_id=user_id,
            bitrix_lead_id=bitrix_lead_id,
        ),
        "RESPONSIBLE_ID": BITRIX_PROJECT_RESPONSIBLE_ID,
        "GROUP_ID": BITRIX_PROJECT_GROUP_ID,
        "CREATED_BY": BITRIX_ASSIGNED_BY_ID,
    }

    if BITRIX_PROJECT_STAGE_ID > 0:
        fields["STAGE_ID"] = BITRIX_PROJECT_STAGE_ID

    if BITRIX_PROJECT_TASK_DEADLINE_HOURS > 0:
        deadline = datetime.now(timezone.utc) + timedelta(hours=BITRIX_PROJECT_TASK_DEADLINE_HOURS)
        fields["DEADLINE"] = deadline.isoformat(timespec="seconds")

    if BITRIX_PROJECT_BIND_TO_CRM and bitrix_lead_id:
        # Bitrix24 taskni CRM lead bilan bog‘lash formati: L_123
        fields["UF_CRM_TASK"] = [f"L_{bitrix_lead_id}"]

    try:
        data = bitrix_post("tasks.task.add", {"fields": fields})
        return extract_bitrix_task_id(data)
    except Exception as first_error:
        # Ba'zi Bitrix portallarda STAGE_ID yoki UF_CRM_TASK ruxsat/sozlama sabab xato berishi mumkin.
        # Shunda minimal majburiy maydonlar bilan qayta urinib ko‘ramiz.
        minimal_fields = dict(fields)
        for optional_key in ["STAGE_ID", "UF_CRM_TASK", "DEADLINE", "CREATED_BY"]:
            minimal_fields.pop(optional_key, None)

        logging.warning("Project task optional fields bilan ochilmadi, minimal fields bilan qayta uriniladi: %s", first_error)
        data = bitrix_post("tasks.task.add", {"fields": minimal_fields})
        return extract_bitrix_task_id(data)


def push_project_task_to_bitrix_if_needed(
    user_id: int,
    sender_name: str,
    username: str,
    customer_name: str,
    phone: str,
    source_text: str,
    bitrix_lead_id: Optional[int] = None,
) -> tuple[bool, Optional[int], str]:
    state = lead_state[user_id]

    if not BITRIX_PROJECT_ENABLE:
        return False, None, "project_disabled"
    if state["sent_to_project_task"]:
        return True, state.get("bitrix_task_id"), "already_sent"
    if not BITRIX_WEBHOOK_URL:
        logging.warning("BITRIX_WEBHOOK_URL berilmagan. Project task ochilmadi.")
        return False, None, "missing_webhook"
    if not BITRIX_PROJECT_GROUP_ID:
        logging.warning("BITRIX_PROJECT_GROUP_ID berilmagan. Project task ochilmadi.")
        return False, None, "missing_project_group_id"

    task_id = create_bitrix_project_task(
        customer_name=customer_name,
        phone=phone,
        source_text=source_text,
        sender_name=sender_name,
        username=username,
        user_id=user_id,
        bitrix_lead_id=bitrix_lead_id,
    )

    state["sent_to_project_task"] = True
    state["bitrix_task_id"] = task_id
    return True, task_id, "created"


# =========================
# CONTACT TOPIC HELPER
# =========================
def _build_contact_topic(result, messages: list[dict]) -> tuple[str, str]:
    """AgentResult dan qisqa mavzu va turini aniqlaydi."""
    if result.order_data:
        od = result.order_data
        parts = [od.get("product", ""), od.get("size", ""), od.get("color", "")]
        info = ", ".join(x for x in parts if x)
        return (f"Buyurtma: {info}" if info else "Buyurtma berdi"), "order"
    if result.needs_human:
        reason = result.human_reason or "murakkab savol"
        return f"Operator kerak: {reason}", "human"
    user_msgs = [m["content"] for m in messages if m["role"] == "user"]
    if user_msgs:
        last = user_msgs[-1]
        text = last if isinstance(last, str) else (
            next((b["text"] for b in last if isinstance(b, dict) and b.get("type") == "text"), "") if isinstance(last, list) else ""
        )
        if text:
            return text[:80].replace("\n", " ").strip(), "general"
    return "Umumiy savol", "general"


# =========================
# EXTERNAL PUSH
# =========================
async def send_lead_to_group(sender, user_id: int, customer_name: str, phone: str, source_text: str):
    sender_name = " ".join(
        x for x in [
            getattr(sender, "first_name", "") or "",
            getattr(sender, "last_name", "") or "",
        ] if x
    ).strip() or getattr(sender, "username", "") or str(user_id)

    username = getattr(sender, "username", "") or ""

    msg = (
        "🆕 YANGI LEAD\n\n"
        f"Ism: {customer_name}\n"
        f"Telefon: {phone}\n"
        f"Telegram name: {sender_name}\n"
        f"Username: @{username if username else 'yoq'}\n"
        f"User ID: {user_id}\n\n"
        f"Mijoz xabari:\n{source_text}"
    )

    entity = await resolve_target_entity(LEAD_GROUP, "lead_group")
    await client.send_message(entity, msg)


# =========================
# AUTO CONTACT → PROJECT TASK
# =========================
async def _try_auto_contact_task(event, sender, user_id: int, text: str):
    """
    Mijoz ismi va telefoni aniqlansa — faqat Bitrix Project task ochadi (CRM ga yozmaydi).
    Xarid qilish shart emas — ism+nomer yetarli.
    """
    state = lead_state[user_id]
    if state["sent_to_project_task"]:
        return
    if not BITRIX_PROJECT_ENABLE or not BITRIX_PROJECT_GROUP_ID:
        return

    name, phone = extract_name_and_phone(text)
    if not (name and phone):
        me = await client.get_me()
        recent = await collect_recent_customer_messages(event.chat_id, me.id, {event.id}, 15)
        full_text = f"{recent}\n{text}".strip()
        name, phone = extract_name_and_phone(full_text)

    if not (name and phone):
        return

    if not state["name"]:
        state["name"] = name
    if not state["phone"]:
        state["phone"] = phone

    sender_name, username = _sender_display(sender, user_id)
    source_text = text or "[contact]"

    try:
        ok, task_id, status = await asyncio.to_thread(
            push_project_task_to_bitrix_if_needed,
            user_id, sender_name, username,
            name, phone, source_text,
            None,
        )
        logging.info("Auto contact task: user=%s name=%s phone=%s task_id=%s status=%s", user_id, name, phone, task_id, status)
    except Exception as e:
        logging.warning("Auto contact task xatosi: %s", e)


# =========================
# DAILY REPORT
# =========================
async def _send_daily_report():
    """Kecha (00:00–23:59 UZT) uchun kunlik hisobot guruhga yuboradi."""
    yesterday = ((datetime.now(timezone.utc) + _REPORT_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        con = _sqlite3.connect(_ANALYTICS_DB)
        rows = con.execute("""
            SELECT user_id, display_name, username, topic, contact_type
            FROM daily_contacts WHERE date = ? ORDER BY id ASC
        """, (yesterday,)).fetchall()
        con.close()
    except Exception as e:
        logging.exception("Daily report DB xatosi: %s", e)
        return

    count = len(rows)
    orders  = sum(1 for r in rows if r[4] == "order")
    humans  = sum(1 for r in rows if r[4] == "human")
    generals = count - orders - humans

    day_names = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
    dt = datetime.strptime(yesterday, "%Y-%m-%d")
    day_name = day_names[dt.weekday()]

    lines = [
        "📊  KUNLIK HISOBOT",
        f"📅  {yesterday}  |  {day_name}",
        "",
        f"📩  Jami murojaat: {count} ta odam",
    ]

    if count > 0:
        lines += ["", "👥  Murojaatchilar:", "─" * 28]
        icons = {"order": "🛒", "human": "🙋", "general": "💬"}
        for i, (uid, name, uname, topic, ctype) in enumerate(rows, 1):
            name_str  = name or "Noma'lum"
            link_str  = f"@{uname}" if uname else f"ID:{uid}"
            icon      = icons.get(ctype, "💬")
            topic_str = (topic or "—")[:90]
            lines.append(f"{i}. 👤 {name_str}  ({link_str})")
            lines.append(f"    {icon} {topic_str}")
        lines += [
            "─" * 28,
            f"🛒 Buyurtmalar: {orders}   🙋 Operatorga: {humans}   💬 Umumiy: {generals}",
        ]
    else:
        lines += ["", "— Bugun hech kim murojaat qilmagan."]

    msg = "\n".join(lines)

    if not LEAD_GROUP:
        logging.warning("LEAD_GROUP berilmagan — daily report yuborilmadi.")
        return
    try:
        entity = await resolve_target_entity(LEAD_GROUP, "lead_group")
        await client.send_message(entity, msg)
        logging.info("Daily report yuborildi: %s | jami=%s", yesterday, count)
    except Exception as e:
        logging.exception("Daily report yuborish xatosi: %s", e)


async def _daily_report_loop():
    """Har kuni 00:00 UZT da _send_daily_report chaqiradi."""
    while True:
        now_uzt = datetime.now(timezone.utc) + _REPORT_TZ
        midnight = (now_uzt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_sec = (midnight - now_uzt).total_seconds()
        logging.info("Daily report %d soniyadan keyin (%s 00:00 UZT)", int(wait_sec), midnight.strftime("%Y-%m-%d"))
        await asyncio.sleep(wait_sec)
        try:
            await _send_daily_report()
        except Exception as e:
            logging.exception("Daily report loop xatosi: %s", e)


# =========================
# ROUTING
# =========================
def should_ignore_message(event, sender, text: str) -> bool:
    if not event.is_private:
        return True
    if event.out:
        return True
    if getattr(sender, "bot", False):
        return True
    if getattr(event.message, "action", None) is not None:
        return True
    if ONLY_TEXT_MESSAGES and not text.strip():
        return True
    return False


def can_reply_now(user_id: int) -> bool:
    now = asyncio.get_event_loop().time()
    return (now - last_reply_time[user_id]) >= MIN_REPLY_INTERVAL


def mark_reply_time(user_id: int):
    last_reply_time[user_id] = asyncio.get_event_loop().time()


async def collect_burst_messages(queue: asyncio.Queue):
    items = []
    first = await queue.get()
    items.append(first)

    start = time.time()
    while len(items) < MAX_BURST_MESSAGES:
        remaining = MESSAGE_BURST_WINDOW - (time.time() - start)
        if remaining <= 0:
            break
        try:
            nxt = await asyncio.wait_for(queue.get(), timeout=remaining)
            items.append(nxt)
        except asyncio.TimeoutError:
            break

    return items


def merge_burst_texts(events_batch: list) -> tuple[str, int]:
    parts = []
    reply_to = None

    for idx, item in enumerate(events_batch, start=1):
        event = item["event"]
        msg_text = (event.raw_text or "").strip()
        if not reply_to:
            reply_to = event.id
        if msg_text:
            parts.append(f"{idx}) {msg_text}")

    merged = "\n".join(parts).strip()
    return merged, reply_to or events_batch[0]["event"].id


# =========================
# COMMUNITY AGENT HANDLER
# =========================
CHAT_HISTORY_LIMIT         = int(os.getenv("COMMUNITY_HISTORY_LIMIT", "60"))
CHAT_HISTORY_DAYS          = int(os.getenv("COMMUNITY_HISTORY_DAYS", "30"))   # Matn tarixi oynasi
CHAT_MEDIA_TRANSCRIBE_HOURS = int(os.getenv("COMMUNITY_MEDIA_HOURS", "48"))   # Ovoz transkripsiya oynasi


def _sender_display(sender, user_id: int) -> tuple[str, str]:
    name = " ".join(
        x for x in [getattr(sender, "first_name", "") or "", getattr(sender, "last_name", "") or ""] if x
    ).strip() or str(user_id)
    username = getattr(sender, "username", "") or ""
    return name, username


async def build_chat_history(chat_id: int, my_id: int) -> list[dict]:
    """
    Telethon orqali to'liq DM tarixini o'qiydi.
    Har bir xabar Claude API formatiga (role + content) o'giriladi.
    Ovozli/video → transkribatsiya, rasm → base64 (faqat so'nggi 3 ta rasm).
    Faqat oxirgi CHAT_HISTORY_DAYS kun ichidagi xabarlar qayta ishlanadi.
    """
    cutoff        = datetime.now(timezone.utc) - timedelta(days=CHAT_HISTORY_DAYS)
    media_cutoff  = datetime.now(timezone.utc) - timedelta(hours=CHAT_MEDIA_TRANSCRIBE_HOURS)
    raw_messages = []
    async for msg in client.iter_messages(chat_id, limit=CHAT_HISTORY_LIMIT):
        if getattr(msg, "action", None) is not None:
            continue
        msg_date = msg.date
        if msg_date.tzinfo is None:
            msg_date = msg_date.replace(tzinfo=timezone.utc)
        if msg_date < cutoff:
            break  # iter_messages yangilikdan eskiga — eski xabar topilsa to'xtaymiz
        raw_messages.append(msg)

    raw_messages.reverse()  # Eskidan yangiga

    # Rasm limitini kuzatish uchun counter
    image_count = sum(1 for m in raw_messages if getattr(m, "photo", None))
    max_images = 3
    images_seen = 0

    result: list[dict] = []

    for msg in raw_messages:
        role = "assistant" if msg.out else "user"

        # ── Matn ──
        if msg.text and not msg.media:
            result.append({"role": role, "content": msg.text.strip()})
            continue

        # ── Matn + media birga (caption) ──
        text_part = (msg.text or "").strip()

        # ── Ovoz / video_note / video / audio ──
        kind = get_media_kind(msg)
        if kind:
            if msg_date >= media_cutoff:
                transcribed = await transcribe_message(client, msg)
            else:
                from media_handler import get_duration, media_label
                dur = get_duration(msg)
                transcribed = f"[{media_label(kind)}{f' — {dur}s' if dur else ''}]"
            content = f"{transcribed or '[media]'}"
            if text_part:
                content = f"{text_part}\n{content}"
            result.append({"role": role, "content": content})
            continue

        # ── Rasm ──
        if getattr(msg, "photo", None):
            images_seen += 1
            # Faqat user xabarlari + so'nggi max_images ta rasm encode qilinadi
            # Claude API assistant turnida image block ruxsat bermaydi
            if role == "user" and image_count - images_seen < max_images:
                encoded = await encode_image_for_claude(client, msg)
                if encoded:
                    if text_part:
                        encoded = [{"type": "text", "text": text_part}] + [
                            b for b in encoded if b.get("type") == "image"
                        ]
                    result.append({"role": role, "content": encoded})
                    continue
            # Assistant rasmlari yoki eski rasmlar — faqat label
            content = text_part or "[Rasm yuborildi]"
            result.append({"role": role, "content": content})
            continue

        # ── GIF ──
        if getattr(msg, "gif", False):
            if role == "user":
                encoded = await encode_gif_for_claude(client, msg)
                if encoded:
                    if text_part:
                        encoded = [{"type": "text", "text": text_part}] + [
                            b for b in encoded if b.get("type") == "image"
                        ]
                    result.append({"role": role, "content": encoded})
                    continue
            result.append({"role": role, "content": text_part or "[GIF yuborildi]"})
            continue

        # ── Stiker ──
        if getattr(msg, "sticker", None):
            if role == "user":
                encoded = await encode_sticker_for_claude(client, msg)
                if encoded:
                    if text_part:
                        encoded = [{"type": "text", "text": text_part}] + [
                            b for b in encoded if b.get("type") == "image"
                        ]
                    result.append({"role": role, "content": encoded})
                    continue
            result.append({"role": role, "content": text_part or "[Stiker yuborildi]"})
            continue

        if text_part:
            result.append({"role": role, "content": text_part})

    # "assistant message prefill" xatosini oldini olish:
    # Claude API oxirgi xabar user bo'lishini talab qiladi
    while result and result[-1]["role"] == "assistant":
        result.pop()

    return result


async def process_with_community_agent(event, sender, user_id: int) -> bool:
    """
    To'liq DM tarixini o'qib, Community Agent orqali javob beradi.
    True qaytaradi agar muvaffaqiyatli ishlagan bo'lsa.
    """
    if not community_agent_inst:
        return False

    me = await client.get_me()
    try:
        messages = await build_chat_history(event.chat_id, me.id)
    except Exception as exc:
        logging.exception("Chat tarixi o'qish xatosi: %s", exc)
        return False

    if not messages:
        return False

    try:
        result: AgentResult = await asyncio.to_thread(community_agent_inst.process, messages)
    except Exception as exc:
        logging.exception("Community agent xatosi: %s", exc)
        return False

    # ── Kunlik statistikaga yoz ──
    try:
        sender_name_dc, uname_dc = _sender_display(sender, user_id)
        topic_dc, ctype_dc = _build_contact_topic(result, messages)
        _save_daily_contact(user_id, sender_name_dc, uname_dc, topic_dc, ctype_dc)
    except Exception as _dc_err:
        logging.warning("daily_contact save: %s", _dc_err)

    # ── Mijozga javob ──
    if result.reply:
        async with client.action(event.chat_id, "typing"):
            await small_typing_delay(result.reply)
            await send_long_message(event, result.reply)
        mark_reply_time(user_id)
        logging.info(
            "Community agent reply user=%s order=%s human=%s reply_len=%s",
            user_id, bool(result.order_data), result.needs_human, len(result.reply)
        )

    # ── Operator xabardor qilish ──
    if (result.order_data or result.needs_human) and LEAD_GROUP:
        try:
            entity = await resolve_target_entity(LEAD_GROUP, "lead_group")
            sender_name, username = _sender_display(sender, user_id)
            tg_link = f"https://t.me/{username}" if username else f"tg://user?id={user_id}"

            if result.order_data:
                od = result.order_data
                notify_msg = (
                    "🛒 YANGI BUYURTMA — Community Agent\n\n"
                    f"👤 Ism:      {od.get('name',     '—')}\n"
                    f"📞 Telefon:  {od.get('phone',    '—')}\n"
                    f"👕 Mahsulot: {od.get('product',  '—')}\n"
                    f"📐 Razmer:   {od.get('size',     '—')}\n"
                    f"🎨 Rang:     {od.get('color',    '—')}\n"
                    f"🔢 Soni:     {od.get('qty',      '—')}\n"
                    f"📍 Viloyat:  {od.get('region',   '—')}\n"
                    f"📍 Tuman:    {od.get('district', '—')}\n"
                    f"📦 Pochta:   {od.get('postal',   '—')}\n\n"
                    f"📱 TG: {sender_name} (@{username or 'yoq'})\n"
                    f"🔗 {tg_link}\n"
                    f"🆔 User ID: {user_id}"
                )
                # Bitrix CRM va project task push
                phone = normalize_phone(od.get("phone", ""))
                if phone and BITRIX_ENABLE and not lead_state[user_id]["sent_to_bitrix"]:
                    try:
                        source_text = (
                            f"Buyurtma: {od.get('product','?')}, "
                            f"razmer {od.get('size','?')}, rang {od.get('color','?')}, "
                            f"soni {od.get('qty','?')}, "
                            f"{od.get('region','?')} / {od.get('district','?')}, "
                            f"pochta: {od.get('postal','?')}"
                        )
                        ok, bitrix_lead_id, bx_status = await asyncio.to_thread(
                            push_lead_to_bitrix_if_needed,
                            user_id, sender_name, username,
                            od.get("name", ""), phone, source_text,
                        )
                        logging.info(
                            "Bitrix CRM (order): ok=%s lead_id=%s status=%s",
                            ok, bitrix_lead_id, bx_status,
                        )
                    except Exception as be:
                        logging.warning("Bitrix CRM push (order): %s", be)

                if phone and not lead_state[user_id]["sent_to_project_task"]:
                    try:
                        ok2, task_id, task_status = await asyncio.to_thread(
                            push_project_task_to_bitrix_if_needed,
                            user_id, sender_name, username,
                            od.get("name", ""), phone, source_text,
                            lead_state[user_id].get("bitrix_lead_id"),
                        )
                        logging.info(
                            "Bitrix project task (order): ok=%s task_id=%s status=%s",
                            ok2, task_id, task_status,
                        )
                    except Exception as be:
                        logging.warning("Bitrix project task push (order): %s", be)

            else:
                notify_msg = (
                    "🙋 OPERATOR KERAK — Community Agent\n\n"
                    f"📌 Sabab: {result.human_reason or 'Murakkab savol'}\n\n"
                    f"📱 TG: {sender_name} (@{username or 'yoq'})\n"
                    f"🔗 {tg_link}\n"
                    f"🆔 User ID: {user_id}"
                )

            await client.send_message(entity, notify_msg)
            logging.info("Operator notified user=%s", user_id)

        except Exception as exc:
            logging.exception("Operator notification xatosi: %s", exc)

    return True


# =========================
# BUSINESS LOGIC
# =========================
async def process_contact_capture(event, sender, user_id: int, incoming_text: str, history_info: dict):
    state = lead_state[user_id]
    my_id = (await client.get_me()).id

    incoming_name, incoming_phone = extract_name_and_phone(incoming_text)
    if incoming_name and not state["name"]:
        state["name"] = incoming_name
    if incoming_phone and not state["phone"]:
        state["phone"] = incoming_phone

    if not (state["name"] and state["phone"]):
        recent_customer_text = await collect_recent_customer_messages(
            chat_id=event.chat_id,
            my_id=my_id,
            exclude_message_ids={event.id},
            limit=20,
        )
        history_text = "\n".join([x for x in [recent_customer_text, incoming_text] if x]).strip()
        if history_text:
            hist_name, hist_phone = extract_name_and_phone(history_text)
            if hist_name and not state["name"]:
                state["name"] = hist_name
            if hist_phone and not state["phone"]:
                state["phone"] = hist_phone

    if not (state["name"] and state["phone"]):
        should_send_template = not history_info.get("manual_outgoing_before_contact")
        if should_send_template:
            state["asked"] = True
            async with client.action(event.chat_id, "typing"):
                await small_typing_delay(NEW_CHAT_CONTACT_TEMPLATE)
                await send_long_message(event, NEW_CHAT_CONTACT_TEMPLATE)
            mark_reply_time(user_id)
            logging.info("Template sent user=%s", user_id)
        else:
            logging.info("Template suppressed because manual outgoing exists; monitoring continues user=%s", user_id)
        return

    sender_name = " ".join(
        x for x in [
            getattr(sender, "first_name", "") or "",
            getattr(sender, "last_name", "") or "",
        ] if x
    ).strip() or getattr(sender, "username", "") or str(user_id)

    username = getattr(sender, "username", "") or ""
    source_text = incoming_text or "[contact sent]"

    if not state["sent_to_group"] and LEAD_GROUP:
        try:
            await send_lead_to_group(
                sender=sender,
                user_id=user_id,
                customer_name=state["name"],
                phone=state["phone"],
                source_text=source_text,
            )
            state["sent_to_group"] = True
            logging.info("Lead pushed to group user=%s", user_id)
        except Exception as e:
            logging.exception("Lead group push error: %s", e)

    if not state["sent_to_bitrix"]:
        try:
            ok, bitrix_id, status = await asyncio.to_thread(
                push_lead_to_bitrix_if_needed,
                user_id,
                sender_name,
                username,
                state["name"],
                state["phone"],
                source_text,
            )
            logging.info("Bitrix CRM result user=%s ok=%s id=%s status=%s", user_id, ok, bitrix_id, status)
        except Exception as e:
            logging.exception("Bitrix CRM push error: %s", e)

    if not state["sent_to_project_task"]:
        try:
            ok, task_id, status = await asyncio.to_thread(
                push_project_task_to_bitrix_if_needed,
                user_id,
                sender_name,
                username,
                state["name"],
                state["phone"],
                source_text,
                state.get("bitrix_lead_id"),
            )
            logging.info("Bitrix project task result user=%s ok=%s task_id=%s status=%s", user_id, ok, task_id, status)
        except Exception as e:
            logging.exception("Bitrix project task push error: %s", e)


async def process_burst_events(events_batch: list):
    first_event = events_batch[0]["event"]

    try:
        sender = await first_event.get_sender()
        if not sender:
            return

        user_id = sender.id
        me = await client.get_me()
        my_id = me.id

        merged_text, _ = merge_burst_texts(events_batch)

        if COMMUNITY_AGENT_ENABLE and community_agent_inst:
            await process_with_community_agent(first_event, sender, user_id)
            # Ism+nomer aniqlansa — faqat Bitrix Project task (CRM emas)
            if merged_text:
                await _try_auto_contact_task(first_event, sender, user_id, merged_text)
        else:
            history_info = await inspect_chat_history(
                chat_id=first_event.chat_id,
                my_id=my_id,
                exclude_message_ids={item["event"].id for item in events_batch},
            )
            await process_contact_capture(first_event, sender, user_id, merged_text, history_info)

    except FloodWaitError as e:
        logging.warning("Flood wait: %s seconds", e.seconds)
        await asyncio.sleep(e.seconds)
    except Exception as e:
        logging.exception("Processing error: %s", e)


# =========================
# PER-USER WORKER
# =========================
async def ensure_user_worker(user_id: int):
    if user_id in user_workers and not user_workers[user_id].done():
        return

    queue = user_queues[user_id]

    async def worker():
        logging.info("Worker started for user %s", user_id)
        while True:
            batch = await collect_burst_messages(queue)
            if not batch:
                continue

            while not can_reply_now(user_id):
                await asyncio.sleep(0.2)

            await process_burst_events(batch)

    user_workers[user_id] = asyncio.create_task(worker())


# =========================
# EVENT HANDLER
# =========================
@client.on(events.NewMessage(incoming=True))
async def handle_new_private_message(event):
    try:
        sender = await event.get_sender()
        if not sender:
            return

        text = (event.raw_text or "").strip()
        user_id = sender.id

        if should_ignore_message(event, sender, text):
            return

        _log_dm_event(user_id)

        if user_id not in user_queues:
            user_queues[user_id] = asyncio.Queue()

        await ensure_user_worker(user_id)
        await user_queues[user_id].put({
            "event": event,
            "created_at": time.time(),
        })

        logging.info(
            "Queued DM from %s | queue_size=%s | text=%s",
            user_id,
            user_queues[user_id].qsize(),
            text[:120],
        )

    except Exception as e:
        logging.exception("Queue handler error: %s", e)


# =========================
# LOGIN
# =========================
async def login_if_needed():
    await client.connect()

    if await client.is_user_authorized():
        return True

    if not PHONE_NUMBER:
        raise ValueError("PHONE_NUMBER .env ichida topilmadi. Masalan: +998901234567")

    logging.info("Telegram login boshlanmoqda: %s", PHONE_NUMBER)

    try:
        await client.send_code_request(PHONE_NUMBER)
    except FloodWaitError as e:
        hours = round(e.seconds / 3600, 2)
        logging.error(
            "Telegram kod yuborishni vaqtincha blokladi. %s sekund kutish kerak (~%s soat).",
            e.seconds,
            hours,
        )
        print(f"\nTelegram vaqtincha blok qo'ygan. Taxminan {hours} soat kuting.\n")
        return False

    code = input("Telegram ichiga kelgan kodni kiriting: ").strip()

    try:
        await client.sign_in(phone=PHONE_NUMBER, code=code)
    except SessionPasswordNeededError:
        password = input("2-step verification passwordni kiriting: ").strip()
        await client.sign_in(password=password)
    except FloodWaitError as e:
        hours = round(e.seconds / 3600, 2)
        logging.error(
            "Login vaqtida flood wait. %s sekund kutish kerak (~%s soat).",
            e.seconds,
            hours,
        )
        print(f"\nTelegram vaqtincha blok qo'ygan. Taxminan {hours} soat kuting.\n")
        return False

    return True


# =========================
# MAIN
# =========================
async def main():
    _init_analytics_db()
    ok = await login_if_needed()
    if ok is False:
        return

    me = await client.get_me()
    username = getattr(me, "username", None) or "no_username"

    logging.info("Logged in as: %s (%s)", username, me.id)
    logging.info("Telegram DM template + contact-capture bot is running")
    logging.info("Mode: ONLY DM / NOT groups / NOT bots")
    logging.info("AI enabled only for contact monitoring/parsing; no AI replies")
    logging.info("Lead group enabled: %s", LEAD_GROUP)
    logging.info("Bitrix CRM enabled: %s", BITRIX_ENABLE)
    logging.info("Bitrix project task enabled: %s | group_id=%s | responsible_id=%s", BITRIX_PROJECT_ENABLE, BITRIX_PROJECT_GROUP_ID, BITRIX_PROJECT_RESPONSIBLE_ID)

    asyncio.create_task(_daily_report_loop())
    logging.info("Daily report loop started (har kuni 00:00 UZT)")

    # Fon prewarm — birinchi mijoz xabariga tayyor bo'lish uchun
    asyncio.create_task(prewarm_whisper())
    asyncio.create_task(asyncio.to_thread(moysklad.prewarm))

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
