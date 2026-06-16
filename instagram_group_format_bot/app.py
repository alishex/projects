import asyncio
import json
import logging
import os
import re
import sqlite3
import html
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
import anthropic
load_dotenv()
# =========================
# CONFIG
# =========================
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "")
PAGE_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
IG_USER_ACCESS_TOKEN = os.getenv("META_IG_USER_ACCESS_TOKEN", "").strip()
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v23.0")
META_PAGE_ID = os.getenv("META_PAGE_ID", "").strip()
META_IG_BUSINESS_ID = os.getenv("META_IG_BUSINESS_ID", "").strip()
META_API_MODE = os.getenv("META_API_MODE", "auto").strip().lower()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
BITRIX_ENABLE = os.getenv("BITRIX_ENABLE", "true").lower() == "true"
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "").rstrip("/")
BITRIX_ASSIGNED_BY_ID = int(os.getenv("BITRIX_ASSIGNED_BY_ID", "1"))
BITRIX_LEAD_TITLE_PREFIX = os.getenv("BITRIX_LEAD_TITLE_PREFIX", "INSTAGRAM")
BITRIX_SOURCE_ID = os.getenv("BITRIX_SOURCE_ID", "INSTAGRAM").strip()
BITRIX_SOURCE_NAME = os.getenv("BITRIX_SOURCE_NAME", "Instagram").strip()
# Sizning Bitrix ro'yxatingizdagi Instagram lead stage/status ID:
# NAME="Instagram", STATUS_ID="UC_SURQ0Z"
BITRIX_LEAD_STATUS_ID = os.getenv("BITRIX_LEAD_STATUS_ID", "UC_SURQ0Z").strip()
BITRIX_LEAD_STATUS_NAME = os.getenv("BITRIX_LEAD_STATUS_NAME", "Instagram").strip()
BITRIX_FORCE_INSTAGRAM_IN_TITLE = os.getenv("BITRIX_FORCE_INSTAGRAM_IN_TITLE", "true").lower() == "true"
BITRIX_USE_INSTAGRAM_NICK_IN_TITLE = os.getenv("BITRIX_USE_INSTAGRAM_NICK_IN_TITLE", "true").lower() == "true"
BITRIX_SOURCE_DESCRIPTION = os.getenv(
    "BITRIX_SOURCE_DESCRIPTION",
    "Instagram DM orqali kelgan lead",
)
BITRIX_TIMEOUT = int(os.getenv("BITRIX_TIMEOUT", "20"))

# Bitrix24 Project / Zadachi integration
BITRIX_PROJECT_ENABLE = os.getenv("BITRIX_PROJECT_ENABLE", "false").lower() == "true"
BITRIX_PROJECT_GROUP_ID = int(os.getenv("BITRIX_PROJECT_GROUP_ID", "0") or "0")
BITRIX_PROJECT_RESPONSIBLE_ID = int(os.getenv("BITRIX_PROJECT_RESPONSIBLE_ID", str(BITRIX_ASSIGNED_BY_ID)) or str(BITRIX_ASSIGNED_BY_ID))
BITRIX_PROJECT_STAGE_ID = int(os.getenv("BITRIX_PROJECT_STAGE_ID", "0") or "0")
BITRIX_PROJECT_TASK_TITLE_PREFIX = os.getenv("BITRIX_PROJECT_TASK_TITLE_PREFIX", "Instagram lead").strip()
BITRIX_PROJECT_TASK_DEADLINE_HOURS = int(os.getenv("BITRIX_PROJECT_TASK_DEADLINE_HOURS", "0") or "0")
BITRIX_PROJECT_BIND_TO_CRM = os.getenv("BITRIX_PROJECT_BIND_TO_CRM", "true").lower() == "true"

# Target video / reklama video orqali kelgan DMlarni alohida stagega yig'ish
TARGET_VIDEO_DETECTION_ENABLE = os.getenv("TARGET_VIDEO_DETECTION_ENABLE", "true").lower() == "true"
BITRIX_TARGET_PROJECT_STAGE_ID = int(os.getenv("BITRIX_TARGET_PROJECT_STAGE_ID", "0") or "0")
BITRIX_TARGET_LEAD_STATUS_ID = os.getenv("BITRIX_TARGET_LEAD_STATUS_ID", "").strip()
BITRIX_TARGET_LEAD_STATUS_NAME = os.getenv("BITRIX_TARGET_LEAD_STATUS_NAME", "Target video").strip()
BITRIX_TARGET_TASK_TITLE_PREFIX = os.getenv("BITRIX_TARGET_TASK_TITLE_PREFIX", "Target video lead").strip()
LEAD_TELEGRAM_TARGET_STATUS_TEXT = os.getenv("LEAD_TELEGRAM_TARGET_STATUS_TEXT", "Target video").strip()
TARGET_VIDEO_DEFAULT_NAME = os.getenv("TARGET_VIDEO_DEFAULT_NAME", "Target video").strip()
TARGET_VIDEO_KEYWORDS = [
    item.strip().lower()
    for item in os.getenv("TARGET_VIDEO_KEYWORDS", "target,reklama,ads").split(",")
    if item.strip()
]

# Duplicate protection
BITRIX_DUPLICATE_CHECK_ENABLE = os.getenv("BITRIX_DUPLICATE_CHECK_ENABLE", "true").lower() == "true"
BITRIX_DUPLICATE_SKIP_PROJECT_TASK = os.getenv("BITRIX_DUPLICATE_SKIP_PROJECT_TASK", "true").lower() == "true"
BITRIX_DUPLICATE_SKIP_CRM_LEAD = os.getenv("BITRIX_DUPLICATE_SKIP_CRM_LEAD", "true").lower() == "true"
LEAD_TELEGRAM_ENABLE = os.getenv("LEAD_TELEGRAM_ENABLE", "false").lower() == "true"
LEAD_TELEGRAM_BOT_TOKEN = os.getenv("LEAD_TELEGRAM_BOT_TOKEN", "").strip()
LEAD_TELEGRAM_CHAT_ID = os.getenv("LEAD_TELEGRAM_CHAT_ID", "").strip()
LEAD_TELEGRAM_SKIP_DUPLICATES = os.getenv("LEAD_TELEGRAM_SKIP_DUPLICATES", "true").lower() == "true"
LEAD_TELEGRAM_RESPONSIBLE_NAME = os.getenv("LEAD_TELEGRAM_RESPONSIBLE_NAME", "").strip()
LEAD_TELEGRAM_SOURCE_TEXT = os.getenv("LEAD_TELEGRAM_SOURCE_TEXT", "Instagram DM").strip()
LEAD_TELEGRAM_STATUS_TEXT = os.getenv("LEAD_TELEGRAM_STATUS_TEXT", BITRIX_LEAD_STATUS_NAME or BITRIX_LEAD_STATUS_ID or "NEW").strip()
LEAD_TELEGRAM_TIMEZONE_OFFSET_HOURS = int(os.getenv("LEAD_TELEGRAM_TIMEZONE_OFFSET_HOURS", "5") or "5")
LEAD_TELEGRAM_PHONE_FORMAT = os.getenv("LEAD_TELEGRAM_PHONE_FORMAT", "local").strip().lower()
ENABLE_CONVERSATION_SYNC = os.getenv("ENABLE_CONVERSATION_SYNC", "true").lower() == "true"
CONVERSATION_SYNC_INTERVAL = int(os.getenv("CONVERSATION_SYNC_INTERVAL", "45"))
SYNC_CONVERSATION_LIMIT = int(os.getenv("SYNC_CONVERSATION_LIMIT", "25"))
SYNC_MESSAGE_LIMIT = int(os.getenv("SYNC_MESSAGE_LIMIT", "20"))
SQLITE_PATH = os.getenv("SQLITE_PATH", "instagram_dm_bot.sqlite3")
MAX_HISTORY_ITEMS = int(os.getenv("MAX_HISTORY_ITEMS", "30"))
MIN_TEMPLATE_RESEND_SECONDS = int(os.getenv("MIN_TEMPLATE_RESEND_SECONDS", "3"))
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "25"))
CONTACT_TEMPLATE = os.getenv(
    "CONTACT_TEMPLATE",
    "Murojatingiz qabul qilindi. Batadsil ma’lumot berishimiz uchun ism va raqamingizni yozib qoldiring. +998 78 555 31 31 raqamidan sizga bog‘lanamiz",
)
if not VERIFY_TOKEN:
    raise ValueError("META_VERIFY_TOKEN .env ichida topilmadi")
def resolve_meta_mode() -> str:
    mode = META_API_MODE
    if mode in {"instagram_login", "instagram", "ig_login"}:
        return "instagram_login"
    if mode in {"facebook_page", "facebook", "page"}:
        return "facebook_page"
    if IG_USER_ACCESS_TOKEN:
        return "instagram_login"
    if PAGE_ACCESS_TOKEN:
        return "facebook_page"
    raise ValueError(
        "Meta token topilmadi. .env ichida META_IG_USER_ACCESS_TOKEN yoki META_PAGE_ACCESS_TOKEN bo‘lishi kerak"
    )
META_MODE = resolve_meta_mode()
EFFECTIVE_PAGE_ID = META_PAGE_ID
EFFECTIVE_IG_BUSINESS_ID = META_IG_BUSINESS_ID
ACTIVE_ACCESS_TOKEN = IG_USER_ACCESS_TOKEN if META_MODE == "instagram_login" else PAGE_ACCESS_TOKEN
if not ACTIVE_ACCESS_TOKEN:
    raise ValueError(
        "Tanlangan Meta rejimi uchun access token topilmadi. Instagram login uchun META_IG_USER_ACCESS_TOKEN, Facebook page uchun META_PAGE_ACCESS_TOKEN kiriting"
    )
# =========================
# LOGGING / APP
# =========================
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("instagram_dm_bot")
app = FastAPI(title="Instagram DM Contact Capture Bot")
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
sync_task: Optional[asyncio.Task] = None
# =========================
# DB
# =========================
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    igsid TEXT PRIMARY KEY,
    ig_username TEXT DEFAULT '',
    name TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    asked_count INTEGER DEFAULT 0,
    template_sent_count INTEGER DEFAULT 0,
    manual_outgoing_before_contact INTEGER DEFAULT 0,
    sent_to_bitrix INTEGER DEFAULT 0,
    bitrix_lead_id TEXT DEFAULT '',
    sent_to_project INTEGER DEFAULT 0,
    bitrix_task_id TEXT DEFAULT '',
    bitrix_duplicate_info TEXT DEFAULT '',
    target_video_name TEXT DEFAULT '',
    target_video_id TEXT DEFAULT '',
    target_video_url TEXT DEFAULT '',
    target_video_raw_json TEXT DEFAULT '',
    sent_to_telegram INTEGER DEFAULT 0,
    last_incoming_at TEXT DEFAULT '',
    last_outgoing_at TEXT DEFAULT '',
    last_template_sent_at TEXT DEFAULT '',
    last_message_text TEXT DEFAULT '',
    history_json TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    contact_captured_at TEXT DEFAULT ''
);
"""
@contextmanager
def db_conn():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def init_db() -> None:
    with db_conn() as conn:
        conn.executescript(SCHEMA_SQL)
        ensure_column(conn, "conversations", "ig_username", "TEXT DEFAULT ''")
        ensure_column(conn, "conversations", "sent_to_project", "INTEGER DEFAULT 0")
        ensure_column(conn, "conversations", "bitrix_task_id", "TEXT DEFAULT ''")
        ensure_column(conn, "conversations", "bitrix_duplicate_info", "TEXT DEFAULT ''")
        ensure_column(conn, "conversations", "target_video_name", "TEXT DEFAULT ''")
        ensure_column(conn, "conversations", "target_video_id", "TEXT DEFAULT ''")
        ensure_column(conn, "conversations", "target_video_url", "TEXT DEFAULT ''")
        ensure_column(conn, "conversations", "target_video_raw_json", "TEXT DEFAULT ''")
        ensure_column(conn, "conversations", "sent_to_telegram", "INTEGER DEFAULT 0")
    logger.info("SQLite initialized: %s", SQLITE_PATH)
def get_conversation(igsid: str) -> dict:
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM conversations WHERE igsid = ?", (igsid,)).fetchone()
        if row:
            data = dict(row)
        else:
            now = utc_now_iso()
            data = {
                "igsid": igsid,
                "ig_username": "",
                "name": "",
                "phone": "",
                "asked_count": 0,
                "template_sent_count": 0,
                "manual_outgoing_before_contact": 0,
                "sent_to_bitrix": 0,
                "bitrix_lead_id": "",
                "sent_to_project": 0,
                "bitrix_task_id": "",
                "bitrix_duplicate_info": "",
                "target_video_name": "",
                "target_video_id": "",
                "target_video_url": "",
                "target_video_raw_json": "",
                "sent_to_telegram": 0,
                "last_incoming_at": "",
                "last_outgoing_at": "",
                "last_template_sent_at": "",
                "last_message_text": "",
                "history_json": "[]",
                "created_at": now,
                "updated_at": now,
                "contact_captured_at": "",
            }
            conn.execute(
                """
                INSERT INTO conversations (
                    igsid, ig_username, name, phone, asked_count, template_sent_count,
                    manual_outgoing_before_contact, sent_to_bitrix, bitrix_lead_id,
                    sent_to_project, bitrix_task_id, bitrix_duplicate_info,
                    target_video_name, target_video_id, target_video_url, target_video_raw_json,
                    sent_to_telegram, last_incoming_at, last_outgoing_at,
                    last_template_sent_at, last_message_text, history_json,
                    created_at, updated_at, contact_captured_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["igsid"], data["ig_username"], data["name"], data["phone"], data["asked_count"],
                    data["template_sent_count"], data["manual_outgoing_before_contact"],
                    data["sent_to_bitrix"], data["bitrix_lead_id"],
                    data["sent_to_project"], data["bitrix_task_id"], data["bitrix_duplicate_info"],
                    data["target_video_name"], data["target_video_id"], data["target_video_url"], data["target_video_raw_json"],
                    data["sent_to_telegram"], data["last_incoming_at"], data["last_outgoing_at"],
                    data["last_template_sent_at"], data["last_message_text"],
                    data["history_json"], data["created_at"], data["updated_at"],
                    data["contact_captured_at"],
                ),
            )
        return data
def update_conversation(igsid: str, fields: Dict[str, Any]) -> None:
    if not fields:
        return
    fields = dict(fields)
    fields["updated_at"] = utc_now_iso()
    keys = list(fields.keys())
    values = [fields[k] for k in keys]
    assignments = ", ".join(f"{k} = ?" for k in keys)
    with db_conn() as conn:
        conn.execute(
            f"UPDATE conversations SET {assignments} WHERE igsid = ?",
            (*values, igsid),
        )
# =========================
# HELPERS
# =========================
def normalize_text(value: str) -> str:
    cleaned = (value or "").strip().lower()
    cleaned = cleaned.replace("’", "'").replace("‘", "'").replace("`", "'")
    return re.sub(r"\s+", " ", cleaned)
TEMPLATE_NORM = normalize_text(CONTACT_TEMPLATE)
def safe_json_loads(value: str, default: Any) -> Any:
    try:
        return json.loads(value) if value else default
    except Exception:
        return default
def trim_history(items: Iterable[dict], limit: int = MAX_HISTORY_ITEMS) -> List[dict]:
    data = list(items)
    return data[-limit:]
def append_history(conv: dict, role: str, text: str, ts: Optional[str] = None) -> List[dict]:
    history = safe_json_loads(conv.get("history_json", "[]"), [])
    history.append(
        {
            "role": role,
            "text": (text or "").strip(),
            "ts": ts or utc_now_iso(),
        }
    )
    return trim_history(history)
def parse_iso_to_ts(value: str) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0
def extract_output_text_raw(response) -> str:
    answer = getattr(response, "output_text", None) or ""
    if answer:
        return answer.strip()
    try:
        collected = []
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) == "message":
                for content in getattr(item, "content", []) or []:
                    if getattr(content, "type", None) == "output_text":
                        collected.append(content.text)
        return "\n".join(collected).strip()
    except Exception:
        return ""
def parse_first_json_object(text: str) -> dict:
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except Exception:
            return {}
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
    if s.startswith("+998") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("998") and len(digits) == 12:
        return f"+{digits}"
    if len(digits) == 9:
        return f"+998{digits}"
    match = re.search(r"(\+?998[\s\-\(\)]*\d{2}[\s\-\(\)]*\d{3}[\s\-\(\)]*\d{2}[\s\-\(\)]*\d{2})", text)
    if match:
        candidate = re.sub(r"\D", "", match.group(1))
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
        "man", "manda", "manga", "menga", "bizga", "biz", "ha", "yoq", "yo‘q",
        "kerak", "yordam", "bor", "bormi", "qancha", "narx", "razmer",
        "rang", "manzil", "zakaz", "buyurtma", "telefon", "raqam", "nomer",
        "ism", "familya", "product", "mahsulot", "price", "help"
    }
    bad_phrases = {
        "assalomu alaykum", "salom alaykum", "menga yordam kerak", "aka manga yordam kerak edi"
    }
    if lowered in bad_phrases:
        return False
    if any(word in bad_words for word in words):
        return False
    for word in words:
        if not re.fullmatch(r"[a-zа-яёўқғҳʼ'`’-]+", word, flags=re.I):
            return False
    return True
def extract_name_and_phone_regex(text: str) -> Tuple[str, str]:
    if not text:
        return "", ""
    phone = normalize_phone(text)
    name = ""
    patterns = [
        r"(?:ismim|ismi|mening ismim|my name is|name)\s*[:\-]?\s*([A-Za-zА-Яа-яЁёЎўҚқҒғҲҳʼ'`’\-\s]{2,40})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I | re.M)
        if match:
            candidate = re.sub(r"\s+", " ", match.group(1).strip(" ,;:-"))
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
def ask_openai_contact_parser(text: str) -> Tuple[str, str]:
    if not anthropic_client or not text.strip():
        return "", ""
    system_prompt = (
        "Sen Instagram DM uchun faqat kontakt aniqlovchi analizatorsan. "
        "Senga kelgan matndan faqat mijozning ISMI va TELEFON raqami bor-yo'qligini aniqlaysan. "
        "Hech qachon taxmin qilma. Salomlashuv, savdo savoli yoki oddiy gapni ism deb qabul qilma. "
        "Telefon faqat aniq ko'rsatilgan raqam bo'lsa olinadi. "
        "Uzbek telefon formatlarini tushun: +998XXXXXXXXX, 998XXXXXXXXX yoki 9 xonali lokal raqam. "
        "Ism bo'lsa 1-3 so'zli real odam ismi bo'lsin. "
        'Javobing faqat JSON bo\'lsin: {"name":"","phone":""}. Boshqa matn yozma.'
    )
    try:
        response = anthropic_client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=256,
            system=system_prompt,
            messages=[{"role": "user", "content": text}],
        )
        raw = response.content[0].text or "{}"
        data = parse_first_json_object(raw)
        name = str(data.get("name") or "").strip()
        phone = str(data.get("phone") or "").strip()
        return name, phone
    except anthropic.RateLimitError as exc:
        logger.warning("Anthropic parser warning: %s", exc)
        return "", ""
    except Exception as exc:
        logger.exception("Anthropic parser error: %s", exc)
        return "", ""
def extract_name_and_phone(text: str) -> Tuple[str, str]:
    regex_name, regex_phone = extract_name_and_phone_regex(text)
    ai_name, ai_phone = ask_openai_contact_parser(text) if anthropic_client else ("", "")
    final_phone = normalize_phone(ai_phone) or regex_phone
    final_name = ""
    ai_name = re.sub(r"\s+", " ", (ai_name or "").strip(" ,;:-"))
    regex_name = re.sub(r"\s+", " ", (regex_name or "").strip(" ,;:-"))
    if ai_name and looks_like_name(ai_name):
        final_name = ai_name
    elif regex_name and looks_like_name(regex_name):
        final_name = regex_name
    return final_name, final_phone
def parse_contact_from_history(history: List[dict]) -> Tuple[str, str]:
    inbound_texts = [item.get("text", "") for item in history if item.get("role") == "inbound" and item.get("text")]
    merged = "\n".join(inbound_texts[-10:]).strip()
    if not merged:
        return "", ""
    return extract_name_and_phone(merged)
def current_business_ids() -> set[str]:
    ids = {str(x) for x in [EFFECTIVE_IG_BUSINESS_ID] if x}
    if META_MODE == "facebook_page" and EFFECTIVE_PAGE_ID:
        ids.add(str(EFFECTIVE_PAGE_ID))
    return ids

def clean_instagram_username(value: Any) -> str:
    """Instagram nikini oddiy ko'rinishga keltiradi: @ belgisiz, ID raqamisiz."""
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("https://www.instagram.com/", "").replace("https://instagram.com/", "")
    text = text.split("?")[0].strip().strip("/").strip()
    if text.startswith("@"):
        text = text[1:].strip()
    # IG scoped ID yoki uzun raqamlarni nick deb qabul qilmaymiz.
    if re.fullmatch(r"\d{8,}", text):
        return ""
    if len(text) > 80:
        return ""
    # Instagram username odatda harf/raqam/dot/underscore dan iborat.
    candidate = re.sub(r"[^A-Za-z0-9._]", "", text)
    return candidate or text

def instagram_nick_label(username: Any) -> str:
    username = clean_instagram_username(username)
    return f"@{username}" if username else "—"

def instagram_nick_plain(username: Any) -> str:
    return clean_instagram_username(username)

def extract_username_from_actor(actor: Any, target_igsid: str = "") -> str:
    if not isinstance(actor, dict):
        return ""
    actor_id = str(actor.get("id") or actor.get("igsid") or "").strip()
    if target_igsid and actor_id and actor_id != str(target_igsid):
        return ""
    for key in ("username", "user_name", "ig_username", "screen_name", "name"):
        username = clean_instagram_username(actor.get(key))
        if username:
            return username
    return ""

def extract_instagram_username_from_event(item: dict, igsid: str) -> str:
    """Webhook payload ichidan mijoz Instagram nickini topishga urinadi."""
    if not isinstance(item, dict):
        return ""
    sender = item.get("sender") or {}
    recipient = item.get("recipient") or {}
    message = item.get("message") or {}
    for actor in (sender, recipient, message.get("from") or {}, message.get("to") or {}):
        username = extract_username_from_actor(actor, igsid)
        if username:
            return username
    return ""

def extract_instagram_username_from_conversation(conversation: dict, igsid: str) -> str:
    """Conversation sync javobidan mijoz Instagram nickini topishga urinadi."""
    if not isinstance(conversation, dict):
        return ""
    participants = conversation.get("participants") or {}
    participant_data = participants.get("data") if isinstance(participants, dict) else participants
    if isinstance(participant_data, list):
        for participant in participant_data:
            username = extract_username_from_actor(participant, igsid)
            if username:
                return username
    messages = ((conversation.get("messages") or {}).get("data") or [])
    for msg in messages:
        username = extract_username_from_actor((msg.get("from") or {}), igsid)
        if username:
            return username
        to_data = ((msg.get("to") or {}).get("data") or [])
        for recipient in to_data:
            username = extract_username_from_actor(recipient, igsid)
            if username:
                return username
    return ""

def fetch_instagram_username(igsid: str) -> str:
    """Meta API orqali IG scoped ID dan username olishga urinadi. Xato bo'lsa jim o'tadi."""
    if not igsid:
        return ""
    try:
        data = graph_get(str(igsid), params={"fields": "id,username,name"})
        return extract_username_from_actor(data, str(igsid))
    except Exception as exc:
        logger.debug("Instagram username resolve skipped igsid=%s: %s", igsid, exc)
        return ""

def save_instagram_username(igsid: str, username: str) -> str:
    username = clean_instagram_username(username)
    if not igsid or not username:
        return ""
    conv = get_conversation(igsid)
    if conv.get("ig_username") != username:
        update_conversation(igsid, {"ig_username": username})
    return username

def get_or_resolve_instagram_username(
    igsid: str,
    raw_event: Optional[dict] = None,
    conversation: Optional[dict] = None,
) -> str:
    conv = get_conversation(igsid)
    username = clean_instagram_username(conv.get("ig_username"))
    if username:
        return username
    username = extract_instagram_username_from_event(raw_event or {}, igsid)
    if not username and conversation:
        username = extract_instagram_username_from_conversation(conversation, igsid)
    if not username:
        username = fetch_instagram_username(igsid)
    return save_instagram_username(igsid, username) or username

def lead_title_person(name: str, ig_username: str) -> str:
    username = instagram_nick_plain(ig_username)
    if BITRIX_USE_INSTAGRAM_NICK_IN_TITLE and username:
        return username
    return name or username or "Instagram mijoz"


def clean_target_video_value(value: Any, limit: int = 160) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text or text.lower() in {"none", "null", "undefined", "-"}:
        return ""
    return text[:limit]


def _first_nested_value(data: Any, keys: Iterable[str]) -> str:
    keys_l = {k.lower() for k in keys}
    found: List[str] = []

    def walk(value: Any) -> None:
        if len(found) >= 1:
            return
        if isinstance(value, dict):
            for k, v in value.items():
                if str(k).lower() in keys_l:
                    cleaned = clean_target_video_value(v)
                    if cleaned:
                        found.append(cleaned)
                        return
            for v in value.values():
                walk(v)
                if found:
                    return
        elif isinstance(value, list):
            for item in value:
                walk(item)
                if found:
                    return

    walk(data)
    return found[0] if found else ""


def _contains_target_signal(data: Any) -> bool:
    raw = json.dumps(data, ensure_ascii=False).lower() if isinstance(data, (dict, list)) else str(data or "").lower()
    signal_words = ["ads_context_data", "ad_id", "ad_title", "ad_name", "campaign", "creative", "referral", "sponsored", "reklama"]
    if any(word in raw for word in signal_words):
        return True
    if TARGET_VIDEO_KEYWORDS:
        for keyword in TARGET_VIDEO_KEYWORDS:
            if not keyword:
                continue
            # Juda qisqa keywordlar (masalan, "ad") JSON ichidagi oddiy so'zlarga ham tushib qolmasligi uchun
            # so'z chegarasi bilan tekshiriladi.
            pattern = r"(?<![A-Za-z0-9_])" + re.escape(keyword) + r"(?![A-Za-z0-9_])"
            if re.search(pattern, raw, flags=re.I):
                return True
    return False


def extract_target_video_info_from_event(item: dict) -> dict:
    """
    Instagram target/reklama video orqali yozilgan DMlarda Meta payload ichidan
    ad/video nomini olishga harakat qiladi. Har xil Meta payload formatlarini
    qo'llash uchun parser ataylab moslashuvchan yozilgan.
    """
    if not TARGET_VIDEO_DETECTION_ENABLE or not isinstance(item, dict):
        return {}

    message = item.get("message") or {}
    postback = item.get("postback") or {}
    candidates = [
        item.get("referral"),
        message.get("referral"),
        postback.get("referral"),
        message.get("ads_context_data"),
        item.get("ads_context_data"),
        item,
    ]

    for candidate in candidates:
        if not isinstance(candidate, (dict, list)):
            continue
        if not _contains_target_signal(candidate):
            continue

        source = _first_nested_value(candidate, ["source", "referral_source", "origin"])
        ad_id = _first_nested_value(candidate, ["ad_id", "adid", "adID", "adgroup_id", "campaign_id", "creative_id"])
        media_id = _first_nested_value(candidate, ["media_id", "post_id", "ig_media_id", "video_id"])
        name = _first_nested_value(
            candidate,
            [
                "ad_title", "ad_name", "title", "name", "headline", "video_title",
                "media_title", "post_title", "caption", "ref", "referral_title"
            ],
        )
        url = _first_nested_value(candidate, ["video_url", "media_url", "source_url", "referer_uri", "url", "permalink"])

        raw = json.dumps(candidate, ensure_ascii=False)
        is_ads_source = source.strip().upper() == "ADS"
        if is_ads_source or ad_id or media_id or name or url:
            return {
                "name": name or TARGET_VIDEO_DEFAULT_NAME,
                "ad_id": ad_id,
                "media_id": media_id,
                "url": url,
                "source": source or "ADS",
                "raw": raw[:2500],
            }

    return {}


def save_target_video_info(igsid: str, info: Optional[dict]) -> dict:
    info = info or {}
    if not igsid or not info:
        return {}
    fields = {
        "target_video_name": clean_target_video_value(info.get("name")) or TARGET_VIDEO_DEFAULT_NAME,
        "target_video_id": clean_target_video_value(info.get("ad_id") or info.get("media_id")),
        "target_video_url": clean_target_video_value(info.get("url"), limit=500),
        "target_video_raw_json": clean_target_video_value(info.get("raw"), limit=2500),
    }
    update_conversation(igsid, fields)
    return {k.replace("target_video_", ""): v for k, v in fields.items() if v}


def target_video_info_from_conversation(conv: dict) -> dict:
    name = clean_target_video_value(conv.get("target_video_name"))
    target_id = clean_target_video_value(conv.get("target_video_id"))
    url = clean_target_video_value(conv.get("target_video_url"), limit=500)
    raw = clean_target_video_value(conv.get("target_video_raw_json"), limit=2500)
    if not (name or target_id or url):
        return {}
    return {"name": name or TARGET_VIDEO_DEFAULT_NAME, "id": target_id, "url": url, "raw": raw}


def target_video_comment_block(info: Optional[dict]) -> str:
    info = info or {}
    name = clean_target_video_value(info.get("name"))
    target_id = clean_target_video_value(info.get("id") or info.get("ad_id") or info.get("media_id"))
    url = clean_target_video_value(info.get("url"), limit=500)
    if not (name or target_id or url):
        return ""
    lines = ["Target video ma’lumoti:"]
    if name:
        lines.append(f"Target video nomi: {name}")
    if target_id:
        lines.append(f"Target video ID: {target_id}")
    if url:
        lines.append(f"Target video link: {url}")
    return "\n".join(lines) + "\n\n"
# =========================
# META GRAPH API
# =========================
def graph_url(path: str) -> str:
    host = "graph.instagram.com" if META_MODE == "instagram_login" else "graph.facebook.com"
    return f"https://{host}/{GRAPH_API_VERSION}/{path.lstrip('/')}"
def meta_auth_params_and_headers(params: Optional[dict] = None) -> Tuple[dict, dict]:
    params = dict(params or {})
    headers: Dict[str, str] = {}
    if META_MODE == "instagram_login":
        headers["Authorization"] = f"Bearer {ACTIVE_ACCESS_TOKEN}"
    else:
        params["access_token"] = ACTIVE_ACCESS_TOKEN
    return params, headers
def graph_get(path: str, params: Optional[dict] = None) -> dict:
    params, headers = meta_auth_params_and_headers(params)
    resp = requests.get(graph_url(path), params=params, headers=headers, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"Meta API error: {data['error']}")
    return data
def graph_post(path: str, payload: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    params, headers = meta_auth_params_and_headers(params)
    resp = requests.post(graph_url(path), params=params, headers=headers, json=payload or {}, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"Meta API error: {data['error']}")
    return data
def discover_meta_ids_if_possible() -> None:
    global EFFECTIVE_PAGE_ID, EFFECTIVE_IG_BUSINESS_ID
    try:
        if META_MODE == "instagram_login":
            if not EFFECTIVE_IG_BUSINESS_ID:
                me = graph_get("me", params={"fields": "id,username"})
                EFFECTIVE_IG_BUSINESS_ID = str(me.get("id") or "").strip()
                logger.info("Discovered IG business id: %s", EFFECTIVE_IG_BUSINESS_ID or "-")
        else:
            if EFFECTIVE_PAGE_ID and not EFFECTIVE_IG_BUSINESS_ID:
                data = graph_get(f"{EFFECTIVE_PAGE_ID}", params={"fields": "instagram_business_account"})
                EFFECTIVE_IG_BUSINESS_ID = str(((data.get("instagram_business_account") or {}).get("id")) or "").strip()
                if EFFECTIVE_IG_BUSINESS_ID:
                    logger.info("Discovered IG business id from page: %s", EFFECTIVE_IG_BUSINESS_ID)
    except Exception as exc:
        logger.warning("Meta ID auto-discovery warning: %s", exc)
def send_instagram_text_message(igsid: str, text: str) -> dict:
    payload = {
        "recipient": {"id": igsid},
        "message": {"text": text},
    }
    if META_MODE == "facebook_page":
        payload["messaging_type"] = "RESPONSE"
        return graph_post("me/messages", payload=payload)
    if not EFFECTIVE_IG_BUSINESS_ID:
        raise RuntimeError("Instagram login rejimida META_IG_BUSINESS_ID topilmadi")
    return graph_post(f"{EFFECTIVE_IG_BUSINESS_ID}/messages", payload=payload)
def fetch_recent_conversations() -> List[dict]:
    fields = (
        f"id,updated_time,participants,messages.limit({SYNC_MESSAGE_LIMIT})"
        "{id,message,created_time,from{id,username,name},to{id,username,name}}"
    )
    if META_MODE == "instagram_login":
        data = graph_get(
            "me/conversations",
            params={
                "limit": SYNC_CONVERSATION_LIMIT,
                "fields": fields,
            },
        )
        return data.get("data", []) or []
    if not EFFECTIVE_PAGE_ID:
        return []
    data = graph_get(
        f"{EFFECTIVE_PAGE_ID}/conversations",
        params={
            "platform": "instagram",
            "limit": SYNC_CONVERSATION_LIMIT,
            "fields": fields,
        },
    )
    return data.get("data", []) or []
# =========================
# BITRIX24
# =========================
def bitrix_method_url(method_name: str) -> str:
    if not BITRIX_WEBHOOK_URL:
        raise ValueError("BITRIX_WEBHOOK_URL .env ichida topilmadi")
    return f"{BITRIX_WEBHOOK_URL}/{method_name}.json"
def bitrix_post(method_name: str, payload: dict) -> dict:
    resp = requests.post(bitrix_method_url(method_name), json=payload, timeout=BITRIX_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Bitrix24 error [{data.get('error')}]: {data.get('error_description')}")
    return data


_bitrix_status_cache: Dict[str, List[dict]] = {}


def normalize_bitrix_lookup(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def bitrix_status_list(entity_id: str) -> List[dict]:
    """
    ENTITY_ID='STATUS' -> lead stadiya/status ro'yxati.
    ENTITY_ID='SOURCE' -> lead source/manba ro'yxati.

    Bitrix'da ko'rinadigan nom "Instagram" bo'ladi, lekin ichki ID
    ko'pincha "UC_..." ko'rinishida bo'ladi. Shu funksiya ID'ni nom orqali ham topadi.
    """
    if entity_id in _bitrix_status_cache:
        return _bitrix_status_cache[entity_id]

    data = bitrix_post("crm.status.list", {"filter": {"ENTITY_ID": entity_id}})
    result = data.get("result", []) or []
    _bitrix_status_cache[entity_id] = result
    return result


def resolve_bitrix_status_id(entity_id: str, preferred_id: str, preferred_name: str) -> str:
    """
    Avval .env ichidagi ID bo'yicha, keyin ko'rinadigan nom bo'yicha qidiradi.
    Topilmasa preferred_id qaytariladi.
    """
    preferred_id = (preferred_id or "").strip()
    preferred_name = (preferred_name or "").strip()

    try:
        items = bitrix_status_list(entity_id)
    except Exception as exc:
        logger.warning(
            "Bitrix %s ro'yxatini o'qib bo'lmadi, .env dagi qiymat ishlatiladi: %s",
            entity_id,
            exc,
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
    prefix = (BITRIX_LEAD_TITLE_PREFIX or "INSTAGRAM").strip()
    title = f"{prefix} - {title_name}" if prefix else title_name

    # Bitrix ichidagi oddiy qidiruvda ham "Instagram" deb chiqishi uchun
    # lead TITLE ichida Instagram so'zi bo'lishini kafolatlaymiz.
    if BITRIX_FORCE_INSTAGRAM_IN_TITLE and "instagram" not in title.lower():
        title = f"INSTAGRAM - {title}"

    return title
def find_bitrix_duplicates_by_phone(phone: str) -> dict:
    payload = {"type": "PHONE", "values": [phone]}
    data = bitrix_post("crm.duplicate.findbycomm", payload)
    return data.get("result", {}) or {}

def get_duplicate_existing_id(duplicates: dict) -> Tuple[Optional[str], str]:
    for key in ("LEAD", "CONTACT", "COMPANY"):
        values = duplicates.get(key, []) or []
        if values:
            return str(values[0]), key.lower()
    return None, ""

def local_phone_already_sent(phone: str, current_igsid: str) -> Optional[dict]:
    if not phone:
        return None
    with db_conn() as conn:
        row = conn.execute(
            """
            SELECT igsid, bitrix_lead_id, bitrix_task_id
            FROM conversations
            WHERE phone = ?
              AND igsid <> ?
              AND (sent_to_bitrix = 1 OR sent_to_project = 1)
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (phone, current_igsid),
        ).fetchone()
        return dict(row) if row else None

def create_bitrix_lead(
    name: str,
    phone: str,
    source_text: str,
    igsid: str,
    ig_username: str = "",
    target_video_info: Optional[dict] = None,
) -> Optional[int]:
    title_name = lead_title_person(name, ig_username)
    source_id = resolve_bitrix_status_id("SOURCE", BITRIX_SOURCE_ID, BITRIX_SOURCE_NAME)
    if target_video_info and (BITRIX_TARGET_LEAD_STATUS_ID or BITRIX_TARGET_LEAD_STATUS_NAME):
        lead_status_id = resolve_bitrix_status_id("STATUS", BITRIX_TARGET_LEAD_STATUS_ID, BITRIX_TARGET_LEAD_STATUS_NAME)
    else:
        lead_status_id = resolve_bitrix_status_id("STATUS", BITRIX_LEAD_STATUS_ID, BITRIX_LEAD_STATUS_NAME)

    comments = (
        f"Instagram DM lead\n"
        f"Ism: {name or '-'}\n"
        f"Telefon: {phone}\n"
        f"Instagram nik: {instagram_nick_label(ig_username)}\n"
        f"{target_video_comment_block(target_video_info)}"
        f"Bitrix source: {source_id}\n"
        f"Bitrix status/stage: {lead_status_id}\n\n"
        f"So‘nggi xabar:\n{source_text}"
    )
    fields = {
        "TITLE": build_bitrix_title(title_name),
        "NAME": name or instagram_nick_plain(ig_username) or "",
        "PHONE": [{"VALUE": phone, "VALUE_TYPE": "WORK"}],
        "COMMENTS": comments,
        "SOURCE_ID": source_id,
        "SOURCE_DESCRIPTION": BITRIX_SOURCE_DESCRIPTION,
        "STATUS_ID": lead_status_id,
        "ASSIGNED_BY_ID": BITRIX_ASSIGNED_BY_ID,
        "OPENED": "Y",
    }
    data = bitrix_post("crm.lead.add", {"fields": fields})
    try:
        return int(data.get("result"))
    except Exception:
        return None

def bitrix_project_deadline() -> Optional[str]:
    if BITRIX_PROJECT_TASK_DEADLINE_HOURS <= 0:
        return None
    return (datetime.now(timezone.utc) + timedelta(hours=BITRIX_PROJECT_TASK_DEADLINE_HOURS)).isoformat()

def build_project_task_title(name: str, phone: str, ig_username: str = "", target_video_info: Optional[dict] = None) -> str:
    prefix = BITRIX_TARGET_TASK_TITLE_PREFIX if target_video_info else BITRIX_PROJECT_TASK_TITLE_PREFIX
    prefix = prefix or "Instagram lead"
    person = lead_title_person(name, ig_username)
    return f"{prefix}: {person} {phone}".strip()

def create_bitrix_project_task(
    name: str,
    phone: str,
    source_text: str,
    igsid: str,
    ig_username: str = "",
    lead_id: Optional[int] = None,
    duplicate_info: str = "",
    target_video_info: Optional[dict] = None,
) -> Optional[int]:
    if not BITRIX_PROJECT_GROUP_ID:
        raise ValueError("BITRIX_PROJECT_GROUP_ID .env ichida topilmadi yoki 0 bo'lib turibdi")

    description = (
        f"Instagram DM orqali kelgan murojaat\n\n"
        f"Ism: {name or '-'}\n"
        f"Telefon: {phone}\n"
        f"Instagram nik: {instagram_nick_label(ig_username)}\n"
        f"{target_video_comment_block(target_video_info)}"
    )
    if lead_id:
        description += f"CRM lead/contact ID: {lead_id}\n"
    if duplicate_info:
        description += f"Dublikat holati: {duplicate_info}\n"
    description += f"\nSo‘nggi xabar:\n{source_text}"

    fields: Dict[str, Any] = {
        "TITLE": build_project_task_title(name, phone, ig_username, target_video_info),
        "DESCRIPTION": description,
        "RESPONSIBLE_ID": BITRIX_PROJECT_RESPONSIBLE_ID or BITRIX_ASSIGNED_BY_ID,
        "GROUP_ID": BITRIX_PROJECT_GROUP_ID,
    }
    stage_id = BITRIX_TARGET_PROJECT_STAGE_ID if target_video_info and BITRIX_TARGET_PROJECT_STAGE_ID > 0 else BITRIX_PROJECT_STAGE_ID
    if stage_id > 0:
        fields["STAGE_ID"] = stage_id
    deadline = bitrix_project_deadline()
    if deadline:
        fields["DEADLINE"] = deadline
    if BITRIX_PROJECT_BIND_TO_CRM and lead_id:
        fields["UF_CRM_TASK"] = [f"L_{lead_id}"]

    payload = {"fields": fields}
    try:
        data = bitrix_post("tasks.task.add", payload)
    except Exception as exc:
        # Ayrim portallarda taskni CRM lead bilan bog'lash maydoni webhook orqali xato berishi mumkin.
        # Shunday bo'lsa, taskni CRM bindingisiz yaratib ko'ramiz.
        if "UF_CRM_TASK" not in fields:
            raise
        logger.warning("Project task CRM bind bilan yaratilmadi, bindingisiz qayta uriniladi: %s", exc)
        fields.pop("UF_CRM_TASK", None)
        data = bitrix_post("tasks.task.add", {"fields": fields})

    result = data.get("result")
    if isinstance(result, dict):
        task = result.get("task") or result
        task_id = task.get("id") or task.get("ID")
    else:
        task_id = result
    try:
        return int(task_id)
    except Exception:
        return None

def push_lead_to_bitrix_if_needed(
    igsid: str,
    name: str,
    phone: str,
    source_text: str,
    target_video_info: Optional[dict] = None,
) -> Tuple[bool, Optional[int], str]:
    conv = get_conversation(igsid)
    ig_username = get_or_resolve_instagram_username(igsid)
    target_video_info = target_video_info or target_video_info_from_conversation(conv)
    if not BITRIX_ENABLE and not BITRIX_PROJECT_ENABLE:
        return False, None, "bitrix_disabled"

    if conv.get("sent_to_bitrix") and (not BITRIX_PROJECT_ENABLE or conv.get("sent_to_project")):
        lead_id = conv.get("bitrix_lead_id")
        return True, int(lead_id) if str(lead_id).isdigit() else None, "already_sent"

    duplicate_info = ""
    existing_id: Optional[str] = None

    local_duplicate = local_phone_already_sent(phone, igsid)
    if local_duplicate:
        existing_id = str(local_duplicate.get("bitrix_lead_id") or "") or None
        duplicate_info = f"local_phone_duplicate: task_id={local_duplicate.get('bitrix_task_id') or '-'}"

    if BITRIX_DUPLICATE_CHECK_ENABLE and phone:
        try:
            duplicates = find_bitrix_duplicates_by_phone(phone)
            crm_duplicate_id, crm_duplicate_type = get_duplicate_existing_id(duplicates)
            if crm_duplicate_id:
                existing_id = crm_duplicate_id
                duplicate_info = f"crm_{crm_duplicate_type}_duplicate: id={crm_duplicate_id}"
        except Exception as exc:
            logger.warning("Bitrix duplicate check error, davom etiladi: %s", exc)

    if duplicate_info:
        fields: Dict[str, Any] = {
            "bitrix_duplicate_info": duplicate_info,
            "contact_captured_at": utc_now_iso(),
        }
        if BITRIX_DUPLICATE_SKIP_CRM_LEAD:
            fields["sent_to_bitrix"] = 1
            fields["bitrix_lead_id"] = str(existing_id or "")
        if BITRIX_DUPLICATE_SKIP_PROJECT_TASK:
            fields["sent_to_project"] = 1
        update_conversation(igsid, fields)

        if BITRIX_DUPLICATE_SKIP_CRM_LEAD and BITRIX_DUPLICATE_SKIP_PROJECT_TASK:
            logger.info("Duplicate skipped igsid=%s phone=%s info=%s", igsid, phone, duplicate_info)
            return True, int(existing_id) if existing_id and str(existing_id).isdigit() else None, "duplicate_found_skipped"

    lead_id: Optional[int] = None
    if BITRIX_ENABLE and not conv.get("sent_to_bitrix") and not (duplicate_info and BITRIX_DUPLICATE_SKIP_CRM_LEAD):
        lead_id = create_bitrix_lead(
            name=name,
            phone=phone,
            source_text=source_text,
            igsid=igsid,
            ig_username=ig_username,
            target_video_info=target_video_info,
        )
        update_conversation(
            igsid,
            {
                "sent_to_bitrix": 1,
                "bitrix_lead_id": str(lead_id or ""),
                "contact_captured_at": utc_now_iso(),
            },
        )
    else:
        saved_id = conv.get("bitrix_lead_id") or existing_id
        lead_id = int(saved_id) if saved_id and str(saved_id).isdigit() else None

    if BITRIX_PROJECT_ENABLE and not conv.get("sent_to_project") and not (duplicate_info and BITRIX_DUPLICATE_SKIP_PROJECT_TASK):
        task_id = create_bitrix_project_task(
            name=name,
            phone=phone,
            source_text=source_text,
            igsid=igsid,
            ig_username=ig_username,
            lead_id=lead_id,
            duplicate_info=duplicate_info,
            target_video_info=target_video_info,
        )
        update_conversation(
            igsid,
            {
                "sent_to_project": 1,
                "bitrix_task_id": str(task_id or ""),
                "contact_captured_at": utc_now_iso(),
            },
        )

    return True, lead_id, "created_or_project_updated"

# =========================
# TELEGRAM MESSAGE FORMAT HELPERS
# =========================
def telegram_html(value: Any) -> str:
    return html.escape(str(value or "—"), quote=False)


def display_phone_for_telegram(phone: str) -> str:
    phone = str(phone or "").strip()
    digits = re.sub(r"\D", "", phone)
    if LEAD_TELEGRAM_PHONE_FORMAT == "local" and digits.startswith("998") and len(digits) == 12:
        return digits[3:]
    if LEAD_TELEGRAM_PHONE_FORMAT == "digits" and digits:
        return digits
    return phone or "—"


def lead_telegram_time() -> str:
    tz = timezone(timedelta(hours=LEAD_TELEGRAM_TIMEZONE_OFFSET_HOURS))
    return datetime.now(tz).strftime("%d.%m.%Y %H:%M")


def bitrix_portal_base_url() -> str:
    match = re.match(r"(https?://[^/]+)", BITRIX_WEBHOOK_URL or "")
    return match.group(1) if match else ""


def bitrix_lead_url(lead_id: Any) -> str:
    lead_id = str(lead_id or "").strip()
    base = bitrix_portal_base_url()
    if not base or not lead_id or lead_id == "-":
        return ""
    return f"{base}/crm/lead/details/{lead_id}/"


_bitrix_user_name_cache: Dict[int, str] = {}


def get_bitrix_user_display_name(user_id: int) -> str:
    if LEAD_TELEGRAM_RESPONSIBLE_NAME:
        return LEAD_TELEGRAM_RESPONSIBLE_NAME
    if not user_id:
        return "—"
    if user_id in _bitrix_user_name_cache:
        return _bitrix_user_name_cache[user_id]
    try:
        data = bitrix_post("user.get", {"ID": user_id})
        users = data.get("result") or []
        if users:
            user = users[0]
            parts = [
                str(user.get("LAST_NAME") or "").strip(),
                str(user.get("NAME") or "").strip(),
            ]
            display = " ".join([p for p in parts if p]).strip()
            if not display:
                display = str(user.get("LOGIN") or user.get("EMAIL") or user_id)
            _bitrix_user_name_cache[user_id] = display
            return display
    except Exception as exc:
        logger.warning("Bitrix user name resolve error: %s", exc)
    return f"ID {user_id}"


def build_telegram_lead_message(
    igsid: str,
    name: str,
    phone: str,
    bitrix_lead_id: Any,
    target_video_info: Optional[dict] = None,
) -> str:
    lead_id_text = str(bitrix_lead_id or "-")
    conv = get_conversation(igsid)
    ig_username = conv.get("ig_username") or get_or_resolve_instagram_username(igsid)
    target_video_info = target_video_info or target_video_info_from_conversation(conv)
    title = build_bitrix_title(lead_title_person(name, ig_username) or display_phone_for_telegram(phone) or "Instagram mijoz")
    responsible_id = BITRIX_ASSIGNED_BY_ID
    responsible_name = get_bitrix_user_display_name(responsible_id)
    lead_link = bitrix_lead_url(lead_id_text)

    lines = [
        "🆕 Yangi lead tushdi",
        "",
        f"👤 Mas’ul: {telegram_html(responsible_name)}",
        f"🆔 Lead ID: {telegram_html(lead_id_text)}",
        f"📌 Nomi: {telegram_html(title)}",
        f"🙋 Mijoz ismi: {telegram_html(name or '—')}",
        f"🧑‍💻 Instagram nik: {telegram_html(instagram_nick_label(ig_username))}",
    ]
    if target_video_info:
        lines.append(f"🎯 Target video: {telegram_html(clean_target_video_value(target_video_info.get('name')) or TARGET_VIDEO_DEFAULT_NAME)}")
    lines.extend([
        f"📞 Telefon: {telegram_html(display_phone_for_telegram(phone))}",
        "✉️ Email: —",
        f"📍 Manba: {telegram_html(LEAD_TELEGRAM_SOURCE_TEXT or 'Instagram DM')}",
        f"📊 Status: {telegram_html((LEAD_TELEGRAM_TARGET_STATUS_TEXT if target_video_info else LEAD_TELEGRAM_STATUS_TEXT) or 'NEW')}",
        f"👨‍💼 Bitrix mas’ul ID: {telegram_html(responsible_id)}",
        f"🕒 Vaqt: {telegram_html(lead_telegram_time())}",
        "",
    ])
    if lead_link:
        lines.append(f'<a href="{html.escape(lead_link, quote=True)}">🔗 Bitrix24’da ochish</a>')
    else:
        lines.append("🔗 Bitrix24’da ochish: —")
    return "\n".join(lines)

# =========================
# OPTIONAL TELEGRAM LEAD PUSH
# =========================
def safe_truncate(value: str, limit: int = 1200) -> str:
    value = (value or "").strip()
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "..."

def send_telegram_lead_if_needed(
    igsid: str,
    name: str,
    phone: str,
    source_text: str,
    bitrix_status: str = "",
    bitrix_lead_id: Optional[int] = None,
    bitrix_task_id: str = "",
    duplicate_info: str = "",
    target_video_info: Optional[dict] = None,
) -> bool:
    conv = get_conversation(igsid)
    if not LEAD_TELEGRAM_ENABLE:
        return False
    if conv.get("sent_to_telegram"):
        return True
    if LEAD_TELEGRAM_SKIP_DUPLICATES and (duplicate_info or conv.get("bitrix_duplicate_info")):
        logger.info(
            "Telegram lead push skipped because duplicate found igsid=%s phone=%s info=%s",
            igsid,
            phone,
            duplicate_info or conv.get("bitrix_duplicate_info"),
        )
        return False
    if not LEAD_TELEGRAM_BOT_TOKEN or not LEAD_TELEGRAM_CHAT_ID:
        logger.warning("Telegram lead push enabled but bot token/chat id missing")
        return False

    lead_id_value = bitrix_lead_id or conv.get("bitrix_lead_id") or "-"
    target_video_info = target_video_info or target_video_info_from_conversation(conv)
    text = build_telegram_lead_message(
        igsid=igsid,
        name=name,
        phone=phone,
        bitrix_lead_id=lead_id_value,
        target_video_info=target_video_info,
    )
    text = safe_truncate(text, 3900)
    url = f"https://api.telegram.org/bot{LEAD_TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        json={
            "chat_id": LEAD_TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram lead push failed: {data}")
    update_conversation(igsid, {"sent_to_telegram": 1})
    return True
# =========================
# BUSINESS LOGIC
# =========================
def should_suppress_template(conv: dict) -> bool:
    return bool(conv.get("manual_outgoing_before_contact"))
def should_resend_template(conv: dict) -> bool:
    last_sent = parse_iso_to_ts(conv.get("last_template_sent_at", ""))
    if not last_sent:
        return True
    return (datetime.now(timezone.utc).timestamp() - last_sent) >= MIN_TEMPLATE_RESEND_SECONDS
def mark_manual_outgoing_if_needed(igsid: str, text: str) -> None:
    if not text.strip():
        return
    if normalize_text(text) == TEMPLATE_NORM:
        update_conversation(
            igsid,
            {
                "last_outgoing_at": utc_now_iso(),
                "last_message_text": text.strip(),
            },
        )
        return
    conv = get_conversation(igsid)
    if conv.get("phone") and conv.get("name"):
        update_conversation(
            igsid,
            {
                "last_outgoing_at": utc_now_iso(),
                "last_message_text": text.strip(),
                "history_json": json.dumps(append_history(conv, "outbound", text), ensure_ascii=False),
            },
        )
        return
    history = append_history(conv, "outbound", text)
    update_conversation(
        igsid,
        {
            "manual_outgoing_before_contact": 1,
            "last_outgoing_at": utc_now_iso(),
            "last_message_text": text.strip(),
            "history_json": json.dumps(history, ensure_ascii=False),
        },
    )
    logger.info("Manual outgoing detected for %s; template suppressed until contact captured", igsid)
async def process_incoming_message(igsid: str, text: str, raw_event: dict) -> None:
    ig_username = await asyncio.to_thread(get_or_resolve_instagram_username, igsid, raw_event=raw_event)
    target_video_info = save_target_video_info(igsid, extract_target_video_info_from_event(raw_event))
    conv = get_conversation(igsid)
    if not target_video_info:
        target_video_info = target_video_info_from_conversation(conv)
    now = utc_now_iso()
    history = append_history(conv, "inbound", text, ts=now)
    direct_name, direct_phone = await asyncio.to_thread(extract_name_and_phone, text)
    hist_name, hist_phone = await asyncio.to_thread(parse_contact_from_history, history)
    name = conv.get("name", "") or direct_name or hist_name
    phone = conv.get("phone", "") or direct_phone or hist_phone
    update_fields = {
        "history_json": json.dumps(history, ensure_ascii=False),
        "last_incoming_at": now,
        "last_message_text": (text or "").strip(),
    }
    if name and not conv.get("name"):
        update_fields["name"] = name
    if phone and not conv.get("phone"):
        update_fields["phone"] = phone
    update_conversation(igsid, update_fields)
    if name and phone:
        logger.info("Contact captured for %s | name=%s | phone=%s", igsid, name, phone)
        ok = False
        lead_id: Optional[int] = None
        status = "bitrix_not_started"
        try:
            ok, lead_id, status = await asyncio.to_thread(
                push_lead_to_bitrix_if_needed,
                igsid,
                name,
                phone,
                text,
                target_video_info,
            )
            logger.info("Bitrix result igsid=%s ok=%s id=%s status=%s", igsid, ok, lead_id, status)
        except Exception as exc:
            status = "bitrix_error"
            logger.exception("Bitrix push error: %s", exc)

        latest_conv = get_conversation(igsid)
        try:
            await asyncio.to_thread(
                send_telegram_lead_if_needed,
                igsid,
                name,
                phone,
                text,
                status,
                lead_id,
                str(latest_conv.get("bitrix_task_id") or ""),
                str(latest_conv.get("bitrix_duplicate_info") or ""),
                target_video_info,
            )
        except Exception as exc:
            logger.exception("Telegram lead push error: %s", exc)
        return
    fresh_conv = get_conversation(igsid)
    if should_suppress_template(fresh_conv):
        logger.info("Template suppressed because manual outgoing exists igsid=%s", igsid)
        return
    if not should_resend_template(fresh_conv):
        logger.info("Template resend throttled igsid=%s", igsid)
        return
    try:
        await asyncio.to_thread(send_instagram_text_message, igsid, CONTACT_TEMPLATE)
        asked_count = int(fresh_conv.get("asked_count") or 0) + 1
        template_count = int(fresh_conv.get("template_sent_count") or 0) + 1
        history_after = append_history(fresh_conv, "outbound", CONTACT_TEMPLATE)
        update_conversation(
            igsid,
            {
                "asked_count": asked_count,
                "template_sent_count": template_count,
                "last_template_sent_at": utc_now_iso(),
                "last_outgoing_at": utc_now_iso(),
                "last_message_text": CONTACT_TEMPLATE,
                "history_json": json.dumps(history_after, ensure_ascii=False),
            },
        )
        logger.info("Template sent to igsid=%s", igsid)
    except Exception as exc:
        logger.exception("Template send error: %s", exc)
# =========================
# WEBHOOK PARSING
# =========================
def extract_event_text(item: dict) -> str:
    message = item.get("message") or {}
    if message.get("text"):
        return str(message.get("text") or "").strip()
    attachments = message.get("attachments") or []
    parts = []
    for att in attachments:
        att_type = att.get("type") or "attachment"
        payload = att.get("payload") or {}
        url = payload.get("url")
        if url:
            parts.append(f"[{att_type}] {url}")
        else:
            parts.append(f"[{att_type}]")
    return "\n".join(parts).strip()
def is_outgoing_echo(item: dict) -> bool:
    message = item.get("message") or {}
    if message.get("is_echo"):
        return True
    sender_id = str((item.get("sender") or {}).get("id") or "")
    recipient_id = str((item.get("recipient") or {}).get("id") or "")
    business_ids = current_business_ids()
    return sender_id in business_ids and sender_id != "" and sender_id != recipient_id
def extract_igsid(item: dict) -> str:
    sender_id = str((item.get("sender") or {}).get("id") or "")
    recipient_id = str((item.get("recipient") or {}).get("id") or "")
    business_ids = current_business_ids()
    if sender_id and sender_id not in business_ids:
        return sender_id
    if recipient_id and recipient_id not in business_ids:
        return recipient_id
    return sender_id or recipient_id
async def process_webhook_payload(payload: dict) -> None:
    if payload.get("object") != "instagram":
        logger.info("Ignoring non-instagram object payload")
        return
    for entry in payload.get("entry", []) or []:
        for item in entry.get("messaging", []) or []:
            igsid = extract_igsid(item)
            if not igsid:
                logger.warning("Could not resolve IGSID from webhook item: %s", item)
                continue
            ig_username = await asyncio.to_thread(get_or_resolve_instagram_username, igsid, raw_event=item)
            text = extract_event_text(item)
            if is_outgoing_echo(item):
                mark_manual_outgoing_if_needed(igsid, text)
                continue
            if not text:
                logger.info("Ignoring empty inbound webhook item for %s", igsid)
                continue
            logger.info("Inbound DM igsid=%s nick=%s text=%s", igsid, instagram_nick_label(ig_username), text[:160])
            await process_incoming_message(igsid, text, item)
# =========================
# OPTIONAL SYNC JOB
# =========================
def infer_counterparty_igsid(conversation: dict) -> str:
    messages = ((conversation.get("messages") or {}).get("data") or [])
    business_ids = current_business_ids()
    for msg in messages:
        from_id = str(((msg.get("from") or {}).get("id") or ""))
        if from_id and from_id not in business_ids:
            return from_id
        to_data = ((msg.get("to") or {}).get("data") or [])
        for recipient in to_data:
            rid = str((recipient or {}).get("id") or "")
            if rid and rid not in business_ids:
                return rid
    return ""
def sync_conversation_snapshot(conversation: dict) -> None:
    igsid = infer_counterparty_igsid(conversation)
    if not igsid:
        return
    get_or_resolve_instagram_username(igsid, conversation=conversation)
    conv = get_conversation(igsid)
    messages = list(reversed(((conversation.get("messages") or {}).get("data") or [])))
    history = safe_json_loads(conv.get("history_json", "[]"), [])
    history_keys = {(item.get("role"), item.get("text"), item.get("ts")) for item in history}
    business_ids = current_business_ids()
    manual_outgoing = bool(conv.get("manual_outgoing_before_contact"))
    for msg in messages:
        text = (msg.get("message") or "").strip()
        if not text:
            continue
        ts = (msg.get("created_time") or "").strip() or utc_now_iso()
        from_id = str(((msg.get("from") or {}).get("id") or ""))
        role = "outbound" if from_id in business_ids else "inbound"
        key = (role, text, ts)
        if key in history_keys:
            continue
        history.append({"role": role, "text": text, "ts": ts})
        history_keys.add(key)
        if role == "outbound" and normalize_text(text) != TEMPLATE_NORM and not (conv.get("name") and conv.get("phone")):
            manual_outgoing = True
    history = trim_history(history)
    name, phone = parse_contact_from_history(history)
    update_fields: Dict[str, Any] = {
        "history_json": json.dumps(history, ensure_ascii=False),
        "manual_outgoing_before_contact": 1 if manual_outgoing else int(conv.get("manual_outgoing_before_contact") or 0),
    }
    if name and not conv.get("name"):
        update_fields["name"] = name
    if phone and not conv.get("phone"):
        update_fields["phone"] = phone
    update_conversation(igsid, update_fields)
    latest_conv = get_conversation(igsid)
    target_video_info = target_video_info_from_conversation(latest_conv)
    final_name = latest_conv.get("name") or name
    final_phone = latest_conv.get("phone") or phone
    if final_name and final_phone and (not latest_conv.get("sent_to_bitrix") or not latest_conv.get("sent_to_project") or not latest_conv.get("sent_to_telegram")):
        source_text = latest_conv.get("last_message_text") or "[sync]"
        ok = False
        lead_id: Optional[int] = None
        status = "bitrix_not_started"
        try:
            ok, lead_id, status = push_lead_to_bitrix_if_needed(
                igsid,
                final_name,
                final_phone,
                source_text,
                target_video_info,
            )
            logger.info("Bitrix sync result igsid=%s ok=%s id=%s status=%s", igsid, ok, lead_id, status)
        except Exception as exc:
            status = "bitrix_error"
            logger.exception("Bitrix sync error: %s", exc)

        latest_conv = get_conversation(igsid)
        try:
            send_telegram_lead_if_needed(
                igsid,
                final_name,
                final_phone,
                source_text,
                status,
                lead_id,
                str(latest_conv.get("bitrix_task_id") or ""),
                str(latest_conv.get("bitrix_duplicate_info") or ""),
                target_video_info,
            )
        except Exception as exc:
            logger.exception("Telegram sync lead push error: %s", exc)
async def conversation_sync_loop() -> None:
    while True:
        try:
            if ENABLE_CONVERSATION_SYNC and (META_MODE == "instagram_login" or EFFECTIVE_PAGE_ID):
                conversations = await asyncio.to_thread(fetch_recent_conversations)
                for conversation in conversations:
                    await asyncio.to_thread(sync_conversation_snapshot, conversation)
                logger.info("Conversation sync complete | count=%s", len(conversations))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Conversation sync loop error: %s", exc)
        await asyncio.sleep(max(CONVERSATION_SYNC_INTERVAL, 15))
# =========================
# ROUTES
# =========================
@app.get("/")
async def root() -> dict:
    return {
        "ok": True,
        "service": "instagram-dm-contact-capture",
        "meta_mode": META_MODE,
        "ai_contact_parser": bool(anthropic_client),
        "bitrix_enabled": BITRIX_ENABLE,
        "bitrix_project_enabled": BITRIX_PROJECT_ENABLE,
        "bitrix_project_group_id": BITRIX_PROJECT_GROUP_ID,
        "bitrix_project_stage_id": BITRIX_PROJECT_STAGE_ID,
        "target_video_detection": TARGET_VIDEO_DETECTION_ENABLE,
        "target_project_stage_id": BITRIX_TARGET_PROJECT_STAGE_ID,
        "telegram_lead_group_enabled": LEAD_TELEGRAM_ENABLE,
        "telegram_skip_duplicates": LEAD_TELEGRAM_SKIP_DUPLICATES,
        "conversation_sync": ENABLE_CONVERSATION_SYNC,
    }
@app.get("/health")
async def health() -> dict:
    return {"ok": True, "time": utc_now_iso()}
@app.get("/webhook")
async def verify_webhook(request: Request) -> Response:
    mode = request.query_params.get("hub.mode")
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and verify_token == VERIFY_TOKEN and challenge:
        logger.info("Webhook verified successfully")
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")
@app.post("/webhook")
async def webhook(request: Request) -> JSONResponse:
    payload = await request.json()
    await process_webhook_payload(payload)
    return JSONResponse({"status": "ok"})
# =========================
# LIFECYCLE
# =========================
@app.on_event("startup")
async def on_startup() -> None:
    global sync_task
    init_db()
    discover_meta_ids_if_possible()
    logger.info("Instagram DM bot starting")
    logger.info("Meta mode: %s", META_MODE)
    logger.info("Effective page id: %s", EFFECTIVE_PAGE_ID or "-")
    logger.info("Effective IG business id: %s", EFFECTIVE_IG_BUSINESS_ID or "-")
    logger.info("Anthropic parser enabled: %s", bool(anthropic_client))
    logger.info("Bitrix CRM lead enabled: %s", BITRIX_ENABLE)
    logger.info("Bitrix project enabled: %s | group_id=%s | stage_id=%s", BITRIX_PROJECT_ENABLE, BITRIX_PROJECT_GROUP_ID, BITRIX_PROJECT_STAGE_ID)
    logger.info("Target video detection: %s | target_project_stage_id=%s", TARGET_VIDEO_DETECTION_ENABLE, BITRIX_TARGET_PROJECT_STAGE_ID)
    logger.info("Telegram lead group enabled: %s | skip_duplicates=%s", LEAD_TELEGRAM_ENABLE, LEAD_TELEGRAM_SKIP_DUPLICATES)
    logger.info("Conversation sync enabled: %s", ENABLE_CONVERSATION_SYNC)
    if ENABLE_CONVERSATION_SYNC and (META_MODE == "instagram_login" or EFFECTIVE_PAGE_ID):
        sync_task = asyncio.create_task(conversation_sync_loop())
@app.on_event("shutdown")
async def on_shutdown() -> None:
    global sync_task
    if sync_task:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass
        sync_task = None
    logger.info("Instagram DM bot stopped")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=False,
        log_level=LOG_LEVEL.lower(),
    )
