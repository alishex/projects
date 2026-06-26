from __future__ import annotations

import logging

import httpx

from app.config import Settings
from app.models import ContactInfo, IncomingMessage
from app.utils.text import html_escape
from app.utils.time_utils import format_for_telegram

log = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def enabled(self) -> bool:
        return bool(
            self.settings.lead_telegram_enable
            and self.settings.lead_telegram_bot_token
            and self.settings.lead_telegram_chat_id
        )

    def send_lead(
        self,
        contact: ContactInfo,
        msg: IncomingMessage,
        bitrix_lead_link: str | None = None,
        bitrix_task_link: str | None = None,
    ) -> bool:
        if not self.enabled():
            log.info("Telegram notifications are disabled or credentials are incomplete")
            return False
        text = self._build_message(contact, msg, bitrix_lead_link, bitrix_task_link)
        url = f"https://api.telegram.org/bot{self.settings.lead_telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.settings.lead_telegram_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            with httpx.Client(timeout=self.settings.http_timeout) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
            log.info("Telegram lead notification sent")
            return True
        except Exception as exc:
            log.error("Telegram send failed: %s", exc)
            return False

    def _build_message(self, contact: ContactInfo, msg: IncomingMessage, bitrix_lead_link: str | None, bitrix_task_link: str | None) -> str:
        phone = contact.phone or "—"
        status_text = self.settings.lead_telegram_target_status_text if msg.target.detected else self.settings.lead_telegram_status_text
        responsible = self.settings.lead_telegram_responsible_name or str(self.settings.bitrix_assigned_by_id)
        nick = msg.full_name or (f"@{msg.username.lstrip('@')}" if msg.username else "—")
        lines = [
            "🆕 <b>Yangi Instagram lead</b>",
            "",
            f"👤 <b>Ism:</b> {html_escape(contact.name or '—')}",
            f"📞 <b>Telefon:</b> {html_escape(phone)}",
            f"📌 <b>Manba:</b> {html_escape(self.settings.lead_telegram_source_text)}",
            f"📊 <b>Status:</b> {html_escape(status_text)}",
            f"🙋 <b>Mas'ul:</b> {html_escape(responsible)}",
            f"🔗 <b>Instagram nick:</b> {html_escape(nick)}",
            f"🆔 <b>Instagram ID:</b> {html_escape(msg.igsid)}",
        ]
        if msg.target.detected:
            lines.append(f"🎯 <b>Target/Reklama:</b> {html_escape(msg.target.name or self.settings.target_video_default_name)}")
        if bitrix_lead_link:
            lines.append(f"🧾 <b>Bitrix lead:</b> <a href=\"{html_escape(bitrix_lead_link)}\">ochish</a>")
        else:
            lines.append("🧾 <b>Bitrix lead:</b> —")
        if bitrix_task_link:
            lines.append(f"📋 <b>Project task:</b> <a href=\"{html_escape(bitrix_task_link)}\">ochish</a>")
        else:
            lines.append("📋 <b>Project task:</b> —")
        lines.append(f"🕒 <b>Vaqt:</b> {html_escape(format_for_telegram(offset_hours=self.settings.lead_telegram_timezone_offset_hours))}")
        return "\n".join(lines)

    def send_operator_needed(self, msg: "IncomingMessage", reason: str = "") -> bool:
        if not self.enabled():
            return False
        nick = msg.full_name or (f"@{msg.username.lstrip('@')}" if msg.username else "—")
        lines = [
            "🙋 <b>OPERATOR KERAK — Community Agent</b>",
            "",
            f"📌 <b>Sabab:</b> {html_escape(reason or 'Murakkab savol')}",
            f"🔗 <b>Instagram nick:</b> {html_escape(nick)}",
            f"🆔 <b>Instagram ID:</b> {html_escape(msg.igsid)}",
            f"🕒 <b>Vaqt:</b> {html_escape(format_for_telegram(offset_hours=self.settings.lead_telegram_timezone_offset_hours))}",
        ]
        return self._send_text("\n".join(lines))

    def send_order_notification(
        self,
        order_data: dict,
        msg: "IncomingMessage",
        bitrix_lead_link: str | None = None,
        bitrix_task_link: str | None = None,
    ) -> bool:
        if not self.enabled():
            return False
        nick = msg.full_name or (f"@{msg.username.lstrip('@')}" if msg.username else "—")
        od = order_data
        lines = [
            "🛒 <b>YANGI BUYURTMA — Community Agent (Instagram)</b>",
            "",
            f"👤 <b>Ism:</b>      {html_escape(od.get('name', '—'))}",
            f"📞 <b>Telefon:</b>  {html_escape(od.get('phone', '—'))}",
            f"👕 <b>Mahsulot:</b> {html_escape(od.get('product', '—'))}",
            f"📐 <b>Razmer:</b>   {html_escape(str(od.get('size', '—')))}",
            f"🎨 <b>Rang:</b>     {html_escape(od.get('color', '—'))}",
            f"🔢 <b>Soni:</b>     {html_escape(str(od.get('qty', '—')))}",
            f"📍 <b>Viloyat:</b>  {html_escape(od.get('region', '—'))}",
            f"📍 <b>Tuman:</b>    {html_escape(od.get('district', '—'))}",
            f"📦 <b>Pochta:</b>   {html_escape(od.get('postal', '—'))}",
            "",
            f"🔗 <b>Instagram nick:</b> {html_escape(nick)}",
            f"🆔 <b>Instagram ID:</b> {html_escape(msg.igsid)}",
        ]
        if bitrix_lead_link:
            lines.append(f"🧾 <b>Bitrix lead:</b> <a href=\"{html_escape(bitrix_lead_link)}\">ochish</a>")
        if bitrix_task_link:
            lines.append(f"📋 <b>Project task:</b> <a href=\"{html_escape(bitrix_task_link)}\">ochish</a>")
        lines.append(f"🕒 <b>Vaqt:</b> {html_escape(format_for_telegram(offset_hours=self.settings.lead_telegram_timezone_offset_hours))}")
        return self._send_text("\n".join(lines))

    def _send_text(self, text: str) -> bool:
        url = f"https://api.telegram.org/bot{self.settings.lead_telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.settings.lead_telegram_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            with httpx.Client(timeout=self.settings.http_timeout) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
            return True
        except Exception as exc:
            log.error("Telegram send failed: %s", exc)
            return False
