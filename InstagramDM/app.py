import asyncio
import json
import logging
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from openai import APIError, OpenAI, RateLimitError
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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4").strip() or "gpt-5.4"
OPENAI_QUOTA_COOLDOWN_SECONDS = int(os.getenv("OPENAI_QUOTA_COOLDOWN_SECONDS", "1800"))
BITRIX_ENABLE = os.getenv("BITRIX_ENABLE", "true").lower() == "true"
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "").rstrip("/")
BITRIX_ASSIGNED_BY_ID = int(os.getenv("BITRIX_ASSIGNED_BY_ID", "1"))
BITRIX_LEAD_TITLE_PREFIX = os.getenv("BITRIX_LEAD_TITLE_PREFIX", "NEW")
BITRIX_SOURCE_DESCRIPTION = os.getenv(
    "BITRIX_SOURCE_DESCRIPTION",
    "Instagram DM orqali kelgan lead",
)
BITRIX_TIMEOUT = int(os.getenv("BITRIX_TIMEOUT", "20"))
LEAD_TELEGRAM_ENABLE = os.getenv("LEAD_TELEGRAM_ENABLE", "false").lower() == "true"
LEAD_TELEGRAM_BOT_TOKEN = os.getenv("LEAD_TELEGRAM_BOT_TOKEN", "")
LEAD_TELEGRAM_CHAT_ID = os.getenv("LEAD_TELEGRAM_CHAT_ID", "")
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
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
sync_task: Optional[asyncio.Task] = None
OPENAI_DISABLED_UNTIL_TS = 0.0
OPENAI_PARSE_CACHE: Dict[str, Tuple[str, str]] = {}
# =========================
# DB
# =========================
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    igsid TEXT PRIMARY KEY,
    name TEXT DEFAULT '',
    profile_name TEXT DEFAULT '',
    profile_username TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    asked_count INTEGER DEFAULT 0,
    template_sent_count INTEGER DEFAULT 0,
    manual_outgoing_before_contact INTEGER DEFAULT 0,
    sent_to_bitrix INTEGER DEFAULT 0,
    bitrix_lead_id TEXT DEFAULT '',
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
def init_db() -> None:
    with db_conn() as conn:
        conn.executescript(SCHEMA_SQL)
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(conversations)").fetchall()}
        if "profile_name" not in existing_cols:
            conn.execute("ALTER TABLE conversations ADD COLUMN profile_name TEXT DEFAULT ''")
        if "profile_username" not in existing_cols:
            conn.execute("ALTER TABLE conversations ADD COLUMN profile_username TEXT DEFAULT ''")
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
                "name": "",
                "profile_name": "",
                "profile_username": "",
                "phone": "",
                "asked_count": 0,
                "template_sent_count": 0,
                "manual_outgoing_before_contact": 0,
                "sent_to_bitrix": 0,
                "bitrix_lead_id": "",
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
                    igsid, name, profile_name, profile_username, phone, asked_count, template_sent_count,
                    manual_outgoing_before_contact, sent_to_bitrix, bitrix_lead_id,
                    sent_to_telegram, last_incoming_at, last_outgoing_at,
                    last_template_sent_at, last_message_text, history_json,
                    created_at, updated_at, contact_captured_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["igsid"], data["name"], data["profile_name"], data["profile_username"],
                    data["phone"], data["asked_count"], data["template_sent_count"], data["manual_outgoing_before_contact"],
                    data["sent_to_bitrix"], data["bitrix_lead_id"], data["sent_to_telegram"],
                    data["last_incoming_at"], data["last_outgoing_at"],
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


def openai_temporarily_disabled() -> bool:
    return OPENAI_DISABLED_UNTIL_TS > datetime.now(timezone.utc).timestamp()

def set_openai_quota_cooldown() -> None:
    global OPENAI_DISABLED_UNTIL_TS
    OPENAI_DISABLED_UNTIL_TS = datetime.now(timezone.utc).timestamp() + max(OPENAI_QUOTA_COOLDOWN_SECONDS, 60)

def build_ai_cache_key(text: str, history_mode: bool) -> str:
    return f"{int(history_mode)}::{normalize_text(text)}"
# =========================
# CONTACT PARSING
# =========================
NAME_HINT_RE = re.compile(
    r"(?:^|\b)(?:ismim|ismi|mening ismim|men\s+|my\s+name\s+is|name)\s*[:\-]?\s*([A-Za-zА-Яа-яЁёЎўҚқҒғҲҳʼ'`’\-\s]{2,40})",
    flags=re.I | re.M,
)
NON_NAME_WORDS = {
    "salom", "assalomu", "alaykum", "va", "rahmat", "aka", "opa", "uka",
    "man", "manda", "manga", "menga", "bizga", "biz", "ha", "yoq", "yo'q", "yo‘q",
    "kerak", "yordam", "bor", "bormi", "qancha", "narx", "razmer", "rang", "rangi",
    "manzil", "zakaz", "buyurtma", "telefon", "raqam", "nomer", "ism", "familya",
    "product", "mahsulot", "price", "help", "hello", "hi", "hey", "alo", "assalamu",
    "aha", "hop", "xop", "xo'p", "xo‘p", "ok", "oke", "okay", "boldi", "bo'ldi",
    "bo‘ldi", "mayli", "hopa", "hmm", "xa", "hopman", "borми", "nima", "qoldimi",
    "qoldi", "borakan", "ranggi", "rangiqoldimi", "keremi", "kerakmi", "есть", "привет",
}
NON_NAME_PHRASES = {
    "assalomu alaykum", "salom alaykum", "menga yordam kerak", "aka manga yordam kerak edi",
    "aha hop", "xo'p", "xo‘p", "bo'ldi", "bo‘ldi", "kok rangi qoldimi", "ko'k rangi qoldimi",
    "ko‘k rangi qoldimi", "assalaumu aleykum", "assaalumu aleykum", "assalaamu alaykum",
}

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

def clean_name_candidate(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip(" ,;:-"))
    cleaned = re.sub(r"^(ismim|ismi|mening ismim|men|my name is|name)\s*[:\-]?\s*", "", cleaned, flags=re.I)
    return cleaned.strip(" ,;:-")

def count_name_words(text: str) -> int:
    return len([w for w in re.split(r"\s+", text.strip()) if w])

def has_explicit_name_marker(text: str) -> bool:
    return bool(NAME_HINT_RE.search(text or ""))

def looks_like_name(text: str) -> bool:
    if not text:
        return False
    cleaned = clean_name_candidate(text)
    lowered = cleaned.lower()
    lowered = lowered.replace("’", "'").replace("‘", "'").replace("`", "'")
    if len(cleaned) < 2 or len(cleaned) > 40:
        return False
    if any(ch.isdigit() for ch in cleaned):
        return False
    if lowered in NON_NAME_PHRASES:
        return False
    words = [w for w in re.split(r"\s+", lowered) if w]
    if not (1 <= len(words) <= 3):
        return False
    if any(word in NON_NAME_WORDS for word in words):
        return False
    if any(len(word) == 1 for word in words):
        return False
    for word in words:
        if not re.fullmatch(r"[a-zа-яёўқғҳʼ'`’\-]+", word, flags=re.I):
            return False
    return True

def extract_name_and_phone_regex(text: str) -> Tuple[str, str]:
    if not text:
        return "", ""
    phone = normalize_phone(text)
    name = ""
    match = NAME_HINT_RE.search(text)
    if match:
        candidate = clean_name_candidate(match.group(1))
        if looks_like_name(candidate):
            name = candidate
    if phone and not name:
        fragments = [frag.strip() for frag in re.split(r"[,;\n]", text) if frag.strip()]
        for frag in fragments:
            if normalize_phone(frag):
                continue
            candidate = clean_name_candidate(frag)
            if looks_like_name(candidate) and (has_explicit_name_marker(frag) or count_name_words(candidate) <= 2):
                name = candidate
                break
    return name, phone

def ask_openai_contact_parser(text: str, history_mode: bool = False) -> Tuple[str, str]:
    global OPENAI_PARSE_CACHE
    if not openai_client or not (text or "").strip() or openai_temporarily_disabled():
        return "", ""
    cache_key = build_ai_cache_key(text, history_mode)
    if cache_key in OPENAI_PARSE_CACHE:
        return OPENAI_PARSE_CACHE[cache_key]
    context_line = (
        "Matn bir nechta xabar tarixidan yig'ilgan bo'lishi mumkin. Turli xabarlardagi ism va telefonni birlashtirishing mumkin. "
        if history_mode else
        "Matn bitta xabar bo'lishi mumkin. Faqat shu xabarda aniq ko'rinib turgan ism va telefonni ol. "
    )
    system_prompt = (
        "Sen Instagram DM uchun faqat kontakt aniqlovchi analizatorsan. "
        "Vazifa: mijozning haqiqiy ISMI va TELEFON raqami bor-yo'qligini aniqlash. "
        f"{context_line}"
        "Hech qachon taxmin qilma. Salomlashuv, tasdiqlovchi gap, savdo savoli, rang/razmer haqidagi matn, "
        "'aha hop', 'xo'p', 'assalomu alaykum', 'kok rangi qoldimi' kabi iboralarni ism deb qabul qilma. "
        "Telefon faqat aniq ko'rsatilgan raqam bo'lsa olinadi. Uzbek formatlarini tushun: +998XXXXXXXXX, 998XXXXXXXXX yoki 9 xonali lokal raqam. "
        "Ism bo'lsa faqat real odam ismi bo'lsin. Ishonching bo'lmasa name ni bo'sh qaytar. "
        "Javobing faqat JSON bo'lsin: {\"name\":\"\",\"phone\":\"\"}. Boshqa matn yozma."
    )
    try:
        response = openai_client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": text}]},
            ],
        )
        raw = extract_output_text_raw(response)
        data = parse_first_json_object(raw)
        name = clean_name_candidate(str(data.get("name") or ""))
        phone = str(data.get("phone") or "").strip()
        result = (name, phone)
        OPENAI_PARSE_CACHE[cache_key] = result
        return result
    except (RateLimitError, APIError) as exc:
        exc_text = str(exc)
        if "insufficient_quota" in exc_text or "quota" in exc_text.lower():
            set_openai_quota_cooldown()
            logger.warning("OpenAI parser disabled for cooldown because quota is insufficient: %s", exc)
        else:
            logger.warning("OpenAI parser warning: %s", exc)
        return "", ""
    except Exception as exc:
        logger.exception("OpenAI parser error: %s", exc)
        return "", ""

def extract_name_and_phone(text: str) -> Tuple[str, str]:
    regex_name, regex_phone = extract_name_and_phone_regex(text)
    final_phone = regex_phone
    should_call_ai = bool(final_phone or has_explicit_name_marker(text or ""))
    ai_name, ai_phone = ask_openai_contact_parser(text) if should_call_ai else ("", "")
    final_phone = normalize_phone(ai_phone) or final_phone
    final_name = ""
    ai_name = clean_name_candidate(ai_name)
    regex_name = clean_name_candidate(regex_name)
    if ai_name and looks_like_name(ai_name):
        final_name = ai_name
    elif regex_name and looks_like_name(regex_name):
        final_name = regex_name
    return final_name, final_phone

def parse_contact_from_history(history: List[dict]) -> Tuple[str, str]:
    inbound_texts = [item.get("text", "") for item in history if item.get("role") == "inbound" and item.get("text")]
    if not inbound_texts:
        return "", ""
    merged = "\n".join(inbound_texts[-10:]).strip()
    history_phone = normalize_phone(merged)
    should_call_ai = bool(history_phone or any(has_explicit_name_marker(t) for t in inbound_texts[-6:]))
    ai_name, ai_phone = ask_openai_contact_parser(merged, history_mode=True) if should_call_ai else ("", "")
    final_phone = normalize_phone(ai_phone) or history_phone
    final_name = clean_name_candidate(ai_name)
    if final_name and looks_like_name(final_name):
        return final_name, final_phone
    if final_phone:
        for text in reversed(inbound_texts[-6:]):
            candidate = clean_name_candidate(text)
            if has_explicit_name_marker(text) and looks_like_name(candidate):
                return candidate, final_phone
    return "", final_phone
def choose_instagram_display_name(profile_name: str, profile_username: str, fallback_name: str = "") -> str:
    profile_name = clean_name_candidate(profile_name)
    profile_username = clean_name_candidate(profile_username)
    fallback_name = clean_name_candidate(fallback_name)
    if profile_name:
        return profile_name
    if profile_username:
        return profile_username
    if fallback_name and looks_like_name(fallback_name):
        return fallback_name
    return ""

def extract_profile_from_webhook_item(item: dict) -> Tuple[str, str]:
    sender = item.get("sender") or {}
    recipient = item.get("recipient") or {}
    business_ids = current_business_ids()
    for obj in (sender, recipient):
        obj_id = str(obj.get("id") or "")
        if obj_id and obj_id in business_ids:
            continue
        candidate_name = str(obj.get("name") or "").strip()
        candidate_username = str(obj.get("username") or obj.get("user_name") or "").strip()
        if candidate_name or candidate_username:
            return candidate_name, candidate_username
    return "", ""

def extract_profile_from_conversation(conversation: dict, igsid: str) -> Tuple[str, str]:
    participants = (conversation.get("participants") or {}).get("data") or []
    for participant in participants:
        pid = str((participant or {}).get("id") or "")
        if pid and pid != str(igsid):
            continue
        profile_name = str((participant or {}).get("name") or "").strip()
        profile_username = str((participant or {}).get("username") or "").strip()
        if profile_name or profile_username:
            return profile_name, profile_username
    return "", ""

def fetch_instagram_profile(igsid: str) -> Tuple[str, str]:
    if not igsid:
        return "", ""
    try:
        data = graph_get(str(igsid), params={"fields": "id,username,name"})
        return str(data.get("name") or "").strip(), str(data.get("username") or "").strip()
    except Exception as exc:
        logger.info("Profile fetch skipped for %s: %s", igsid, exc)
        return "", ""

def current_business_ids() -> set[str]:
    ids = {str(x) for x in [EFFECTIVE_IG_BUSINESS_ID] if x}
    if META_MODE == "facebook_page" and EFFECTIVE_PAGE_ID:
        ids.add(str(EFFECTIVE_PAGE_ID))
    return ids
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
        f"id,updated_time,participants{{id,username,name}},messages.limit({SYNC_MESSAGE_LIMIT})"
        "{id,message,created_time,from,to}"
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
def find_bitrix_duplicates_by_phone(phone: str) -> dict:
    payload = {"type": "PHONE", "values": [phone]}
    data = bitrix_post("crm.duplicate.findbycomm", payload)
    return data.get("result", {}) or {}
def create_bitrix_lead(name: str, phone: str, source_text: str, igsid: str) -> Optional[int]:
    title_name = name or "Instagram mijoz"
    comments = (
        f"Instagram DM lead\n"
        f"Ism: {name or '-'}\n"
        f"Telefon: {phone}\n"
        f"IGSID: {igsid}\n\n"
        f"So‘nggi xabar:\n{source_text}"
    )
    fields = {
        "TITLE": f"{BITRIX_LEAD_TITLE_PREFIX} - {title_name}",
        "NAME": name or "",
        "PHONE": [{"VALUE": phone, "VALUE_TYPE": "WORK"}],
        "COMMENTS": comments,
        "SOURCE_DESCRIPTION": BITRIX_SOURCE_DESCRIPTION,
        "ASSIGNED_BY_ID": BITRIX_ASSIGNED_BY_ID,
        "OPENED": "Y",
    }
    data = bitrix_post("crm.lead.add", {"fields": fields})
    try:
        return int(data.get("result"))
    except Exception:
        return None
def push_lead_to_bitrix_if_needed(igsid: str, name: str, phone: str, source_text: str) -> Tuple[bool, Optional[int], str]:
    conv = get_conversation(igsid)
    if not BITRIX_ENABLE:
        return False, None, "bitrix_disabled"
    if conv.get("sent_to_bitrix"):
        lead_id = conv.get("bitrix_lead_id")
        return True, int(lead_id) if str(lead_id).isdigit() else None, "already_sent"
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
        update_conversation(
            igsid,
            {
                "sent_to_bitrix": 1,
                "bitrix_lead_id": str(existing_id or ""),
                "contact_captured_at": utc_now_iso(),
            },
        )
        return True, int(existing_id) if existing_id and str(existing_id).isdigit() else None, "duplicate_found"
    lead_id = create_bitrix_lead(name=name, phone=phone, source_text=source_text, igsid=igsid)
    update_conversation(
        igsid,
        {
            "sent_to_bitrix": 1,
            "bitrix_lead_id": str(lead_id or ""),
            "contact_captured_at": utc_now_iso(),
        },
    )
    return True, lead_id, "created"
# =========================
# OPTIONAL TELEGRAM LEAD PUSH
# =========================
def send_telegram_lead_if_needed(igsid: str, name: str, phone: str, source_text: str) -> bool:
    conv = get_conversation(igsid)
    if not LEAD_TELEGRAM_ENABLE:
        return False
    if conv.get("sent_to_telegram"):
        return True
    if not LEAD_TELEGRAM_BOT_TOKEN or not LEAD_TELEGRAM_CHAT_ID:
        logger.warning("Telegram lead push enabled but bot token/chat id missing")
        return False
    text = (
        "🆕 YANGI INSTAGRAM LEAD\n\n"
        f"Ism: {name}\n"
        f"Telefon: {phone}\n"
        f"IGSID: {igsid}\n\n"
        f"Mijoz xabari:\n{source_text}"
    )
    url = f"https://api.telegram.org/bot{LEAD_TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={"chat_id": LEAD_TELEGRAM_CHAT_ID, "text": text}, timeout=HTTP_TIMEOUT)
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
    conv = get_conversation(igsid)
    now = utc_now_iso()
    history = append_history(conv, "inbound", text, ts=now)
    direct_name, direct_phone = extract_name_and_phone(text)
    hist_name, hist_phone = parse_contact_from_history(history)
    phone = conv.get("phone", "") or direct_phone or hist_phone

    profile_name, profile_username = extract_profile_from_webhook_item(raw_event)
    if not profile_name and not profile_username and (not conv.get("profile_name") and not conv.get("profile_username")):
        fetched_name, fetched_username = await asyncio.to_thread(fetch_instagram_profile, igsid)
        profile_name = profile_name or fetched_name
        profile_username = profile_username or fetched_username

    ai_or_explicit_name = direct_name or hist_name
    lead_name = ai_or_explicit_name or choose_instagram_display_name(
        profile_name or conv.get("profile_name", ""),
        profile_username or conv.get("profile_username", ""),
        conv.get("name", ""),
    )

    update_fields = {
        "history_json": json.dumps(history, ensure_ascii=False),
        "last_incoming_at": now,
        "last_message_text": (text or "").strip(),
    }
    if profile_name:
        update_fields["profile_name"] = profile_name
    if profile_username:
        update_fields["profile_username"] = profile_username
    if lead_name:
        update_fields["name"] = lead_name
    if phone and not conv.get("phone"):
        update_fields["phone"] = phone
    update_conversation(igsid, update_fields)

    if lead_name and phone:
        logger.info("Contact captured for %s | lead_name=%s | phone=%s", igsid, lead_name, phone)
        try:
            await asyncio.to_thread(send_telegram_lead_if_needed, igsid, lead_name, phone, text)
        except Exception as exc:
            logger.exception("Telegram lead push error: %s", exc)
        try:
            ok, lead_id, status = await asyncio.to_thread(
                push_lead_to_bitrix_if_needed,
                igsid,
                lead_name,
                phone,
                text,
            )
            logger.info("Bitrix result igsid=%s ok=%s id=%s status=%s", igsid, ok, lead_id, status)
        except Exception as exc:
            logger.exception("Bitrix push error: %s", exc)
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
            text = extract_event_text(item)
            if is_outgoing_echo(item):
                mark_manual_outgoing_if_needed(igsid, text)
                continue
            if not text:
                logger.info("Ignoring empty inbound webhook item for %s", igsid)
                continue
            logger.info("Inbound DM igsid=%s text=%s", igsid, text[:160])
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
    conv = get_conversation(igsid)
    profile_name, profile_username = extract_profile_from_conversation(conversation, igsid)
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
    hist_name, phone = parse_contact_from_history(history)
    lead_name = hist_name or choose_instagram_display_name(
        profile_name or conv.get("profile_name", ""),
        profile_username or conv.get("profile_username", ""),
        conv.get("name", ""),
    )
    update_fields: Dict[str, Any] = {
        "history_json": json.dumps(history, ensure_ascii=False),
        "manual_outgoing_before_contact": 1 if manual_outgoing else int(conv.get("manual_outgoing_before_contact") or 0),
    }
    if profile_name:
        update_fields["profile_name"] = profile_name
    if profile_username:
        update_fields["profile_username"] = profile_username
    if lead_name:
        update_fields["name"] = lead_name
    if phone and not conv.get("phone"):
        update_fields["phone"] = phone
    update_conversation(igsid, update_fields)
    latest_conv = get_conversation(igsid)
    final_name = latest_conv.get("name") or lead_name
    final_phone = latest_conv.get("phone") or phone
    if final_name and final_phone and not latest_conv.get("sent_to_bitrix"):
        try:
            send_telegram_lead_if_needed(igsid, final_name, final_phone, latest_conv.get("last_message_text") or "[sync]")
        except Exception as exc:
            logger.exception("Telegram sync lead push error: %s", exc)
        try:
            ok, lead_id, status = push_lead_to_bitrix_if_needed(
                igsid,
                final_name,
                final_phone,
                latest_conv.get("last_message_text") or "[sync]",
            )
            logger.info("Bitrix sync result igsid=%s ok=%s id=%s status=%s", igsid, ok, lead_id, status)
        except Exception as exc:
            logger.exception("Bitrix sync error: %s", exc)
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
        "ai_contact_parser": bool(openai_client),
        "bitrix_enabled": BITRIX_ENABLE,
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
    logger.info("OpenAI parser enabled: %s", bool(openai_client))
    logger.info("Bitrix enabled: %s", BITRIX_ENABLE)
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
