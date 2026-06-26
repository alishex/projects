from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


_TRUE = {"1", "true", "yes", "y", "on"}
_FALSE = {"0", "false", "no", "n", "off"}


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    return default


def _int(name: str, default: int = 0) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _float(name: str, default: float = 0.0) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(slots=True)
class Settings:
    app_host: str = _env("APP_HOST", "0.0.0.0")
    app_port: int = _int("APP_PORT", 8000)
    app_env: str = _env("APP_ENV", "production")
    log_level: str = _env("LOG_LEVEL", "INFO")
    sqlite_path: str = _env("SQLITE_PATH", "data/instagram_dm_bot.sqlite3")
    http_timeout: int = _int("HTTP_TIMEOUT", 25)
    max_history_items: int = _int("MAX_HISTORY_ITEMS", 30)
    min_template_resend_seconds: int = _int("MIN_TEMPLATE_RESEND_SECONDS", 86400)

    meta_api_mode: str = _env("META_API_MODE", "instagram_login")
    meta_verify_token: str = _env("META_VERIFY_TOKEN", "replace_me")
    meta_app_secret: str = _env("META_APP_SECRET", "replace_me")
    meta_ig_user_access_token: str = _env("META_IG_USER_ACCESS_TOKEN", "replace_me")
    meta_page_access_token: str = _env("META_PAGE_ACCESS_TOKEN", "")
    graph_api_version: str = _env("GRAPH_API_VERSION", "v20.0")
    meta_page_id: str = _env("META_PAGE_ID", "")
    meta_ig_business_id: str = _env("META_IG_BUSINESS_ID", "replace_me")
    enable_conversation_sync: bool = _bool("ENABLE_CONVERSATION_SYNC", True)
    conversation_sync_interval: int = _int("CONVERSATION_SYNC_INTERVAL", 45)
    sync_conversation_limit: int = _int("SYNC_CONVERSATION_LIMIT", 25)
    sync_message_limit: int = _int("SYNC_MESSAGE_LIMIT", 20)

    anthropic_api_key: str = _env("ANTHROPIC_API_KEY", "replace_me")
    anthropic_model: str = _env("ANTHROPIC_MODEL", "claude-opus-4-8")

    bitrix_enable: bool = _bool("BITRIX_ENABLE", True)
    bitrix_webhook_url: str = _env("BITRIX_WEBHOOK_URL", "")
    bitrix_assigned_by_id: int = _int("BITRIX_ASSIGNED_BY_ID", 63)
    bitrix_lead_title_prefix: str = _env("BITRIX_LEAD_TITLE_PREFIX", "INSTAGRAM")
    bitrix_source_id: str = _env("BITRIX_SOURCE_ID", "INSTAGRAM")
    bitrix_source_name: str = _env("BITRIX_SOURCE_NAME", "Instagram")
    bitrix_lead_status_id: str = _env("BITRIX_LEAD_STATUS_ID", "")
    bitrix_lead_status_name: str = _env("BITRIX_LEAD_STATUS_NAME", "Instagram")
    bitrix_force_instagram_in_title: bool = _bool("BITRIX_FORCE_INSTAGRAM_IN_TITLE", True)
    bitrix_use_instagram_nick_in_title: bool = _bool("BITRIX_USE_INSTAGRAM_NICK_IN_TITLE", True)
    bitrix_source_description: str = _env("BITRIX_SOURCE_DESCRIPTION", "Instagram DM orqali kelgan lead")
    bitrix_timeout: int = _int("BITRIX_TIMEOUT", 20)

    bitrix_project_enable: bool = _bool("BITRIX_PROJECT_ENABLE", True)
    bitrix_project_group_id: int = _int("BITRIX_PROJECT_GROUP_ID", 15)
    bitrix_project_responsible_id: int = _int("BITRIX_PROJECT_RESPONSIBLE_ID", 63)
    bitrix_project_stage_id: int = _int("BITRIX_PROJECT_STAGE_ID", 303)
    bitrix_project_task_title_prefix: str = _env("BITRIX_PROJECT_TASK_TITLE_PREFIX", "Instagram lead")
    bitrix_project_task_deadline_hours: int = _int("BITRIX_PROJECT_TASK_DEADLINE_HOURS", 0)
    bitrix_project_bind_to_crm: bool = _bool("BITRIX_PROJECT_BIND_TO_CRM", True)

    bitrix_duplicate_check_enable: bool = _bool("BITRIX_DUPLICATE_CHECK_ENABLE", True)
    bitrix_duplicate_skip_project_task: bool = _bool("BITRIX_DUPLICATE_SKIP_PROJECT_TASK", True)
    bitrix_duplicate_skip_crm_lead: bool = _bool("BITRIX_DUPLICATE_SKIP_CRM_LEAD", True)

    lead_telegram_enable: bool = _bool("LEAD_TELEGRAM_ENABLE", True)
    lead_telegram_bot_token: str = _env("LEAD_TELEGRAM_BOT_TOKEN", "")
    lead_telegram_chat_id: str = _env("LEAD_TELEGRAM_CHAT_ID", "")
    lead_telegram_skip_duplicates: bool = _bool("LEAD_TELEGRAM_SKIP_DUPLICATES", True)
    lead_telegram_responsible_name: str = _env("LEAD_TELEGRAM_RESPONSIBLE_NAME", "")
    lead_telegram_source_text: str = _env("LEAD_TELEGRAM_SOURCE_TEXT", "Instagram DM")
    lead_telegram_status_text: str = _env("LEAD_TELEGRAM_STATUS_TEXT", "Instagram")
    lead_telegram_target_status_text: str = _env("LEAD_TELEGRAM_TARGET_STATUS_TEXT", "Instagram target")
    lead_telegram_timezone_offset_hours: int = _int("LEAD_TELEGRAM_TIMEZONE_OFFSET_HOURS", 5)
    lead_telegram_phone_format: str = _env("LEAD_TELEGRAM_PHONE_FORMAT", "local")

    contact_template: str = _env(
        "CONTACT_TEMPLATE",
        "Murojatingiz qabul qilindi. Batafsil ma’lumot berishimiz uchun ism va raqamingizni yozib qoldiring. +998 78 555 31 31 raqamidan sizga bog‘lanamiz.",
    )

    target_video_detection_enable: bool = _bool("TARGET_VIDEO_DETECTION_ENABLE", True)
    bitrix_target_project_stage_id: int = _int("BITRIX_TARGET_PROJECT_STAGE_ID", 0)
    bitrix_target_project_stage_name: str = _env("BITRIX_TARGET_PROJECT_STAGE_NAME", "Instagram target")
    bitrix_target_lead_status_id: str = _env("BITRIX_TARGET_LEAD_STATUS_ID", "")
    bitrix_target_lead_status_name: str = _env("BITRIX_TARGET_LEAD_STATUS_NAME", "Instagram target")
    bitrix_target_task_title_prefix: str = _env("BITRIX_TARGET_TASK_TITLE_PREFIX", "Instagram target lead")
    target_video_default_name: str = _env("TARGET_VIDEO_DEFAULT_NAME", "Instagram target")
    target_video_keywords: str = _env("TARGET_VIDEO_KEYWORDS", "target,reklama,ads,ad,instagram target")

    # Community Agent (Claude AI auto-reply)
    community_agent_enable: bool = _bool("COMMUNITY_AGENT_ENABLE", True)
    community_work_start: int = _int("COMMUNITY_WORK_START", 9)
    community_work_end: int = _int("COMMUNITY_WORK_END", 22)
    community_address: str = _env("COMMUNITY_ADDRESS", "Toshkent sh., Bunyodkor Savdo Majmuasi (Korzinka -1-qavat, er osti qavat), metro: Mirzo Ulug'bek")
    community_phone: str = _env("COMMUNITY_PHONE", "+998 78 555 31 31")

    # MoySklad stok
    moysklad_token: str = _env("MOYSKLAD_TOKEN", "")

    def ensure_dirs(self) -> None:
        Path(self.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
        Path("data").mkdir(exist_ok=True)

    @property
    def instagram_access_token(self) -> str:
        if self.meta_api_mode == "facebook_page" and self.meta_page_access_token:
            return self.meta_page_access_token
        return self.meta_ig_user_access_token

    @property
    def secret_values(self) -> list[str]:
        return [
            self.meta_app_secret,
            self.meta_ig_user_access_token,
            self.meta_page_access_token,
            self.anthropic_api_key,
            self.bitrix_webhook_url,
            self.lead_telegram_bot_token,
        ]


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
