from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.config import Settings, get_settings
from app.database import Database
from app.models import IncomingMessage
from app.services.bitrix_service import BitrixService
from app.services.duplicate_service import DuplicateService
from app.services.instagram_service import InstagramService
from app.services.meta_signature import verify_meta_signature
from app.services.openai_parser import ContactParser
from app.services.telegram_service import TelegramService
from app.utils.text import history_to_text, history_to_incoming_text
from app.utils.time_utils import parse_iso, utc_now_iso

log = logging.getLogger(__name__)
router = APIRouter()


def get_db(request: Request) -> Database:
    return request.app.state.db


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    if hub_mode == "subscribe" and hub_verify_token == settings.meta_verify_token:
        log.info("Meta webhook verified")
        return PlainTextResponse(hub_challenge or "")
    log.warning("Meta webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> dict[str, str]:
    raw_body = await request.body()
    if not verify_meta_signature(raw_body, x_hub_signature_256, settings.meta_app_secret):
        raise HTTPException(status_code=403, detail="Invalid signature")
    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("Invalid webhook JSON: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc
    log.info("Webhook payload received")
    background_tasks.add_task(process_payload, payload, settings, db)
    return {"status": "EVENT_RECEIVED"}


def process_payload(payload: dict[str, Any], settings: Settings, db: Database) -> None:
    instagram = InstagramService(settings)
    for msg in instagram.extract_messages(payload):
        try:
            process_message(msg, settings, db, instagram)
        except Exception as exc:  # noqa: BLE001
            log.exception("Message processing failed for event=%s: %s", msg.event_id, exc)


def process_message(msg: IncomingMessage, settings: Settings, db: Database, instagram: InstagramService | None = None) -> None:
    instagram = instagram or InstagramService(settings)
    if not db.mark_event_processing(msg.event_id):
        log.info("Duplicate webhook event skipped: %s", msg.event_id)
        return

    if msg.is_echo:
        db.upsert_conversation(msg.igsid, manual_outgoing_detected=1, username=msg.username, full_name=msg.full_name)
        db.append_history(msg.igsid, "outgoing", msg.text or "", settings.max_history_items)
        log.info("Manual outgoing/echo event marked for igsid=%s", msg.igsid)
        return

    # Instagram profildan ism va usernameni olish (webhook da ko'pincha bo'lmaydi)
    if not msg.full_name and not msg.username:
        profile = instagram.get_user_profile(msg.igsid)
        if profile:
            msg.full_name = profile.get("name") or msg.full_name
            msg.username = profile.get("username") or msg.username
            log.info("Instagram profile fetched for igsid=%s full_name=%s username=%s", msg.igsid, msg.full_name, msg.username)

    row = db.upsert_conversation(
        msg.igsid,
        username=msg.username,
        full_name=msg.full_name,
        target_detected=1 if msg.target.detected else 0,
        target_name=msg.target.name,
    )
    db.append_history(msg.igsid, "incoming", msg.text or "", settings.max_history_items, {"event_id": msg.event_id})
    history = db.get_history(msg.igsid)

    # Parser faqat INCOMING (mijoz) xabarlarini o'qiydi — bot templatelaridan telefon olmaydi
    incoming_text = history_to_incoming_text(history, settings.max_history_items)

    parser = ContactParser(settings)
    contact = parser.parse(incoming_text)
    if contact.phone and not contact.name:
        contact.name = msg.full_name or (msg.username.lstrip("@") if msg.username else None)

    if not contact.phone:
        maybe_send_template(settings, db, instagram, msg)
        return

    bitrix = BitrixService(settings)
    duplicate_service = DuplicateService(settings, db, bitrix)
    duplicate = duplicate_service.check(contact.phone, msg.igsid)
    if duplicate.duplicate:
        if settings.bitrix_duplicate_skip_crm_lead and settings.lead_telegram_skip_duplicates:
            db.upsert_conversation(msg.igsid, phone=contact.phone, contact_found=1)
            log.info("Lead skipped because duplicate policy is enabled. reason=%s", duplicate.reason)
            return

    lead_id = duplicate.bitrix_lead_id if duplicate.duplicate and settings.bitrix_duplicate_skip_crm_lead else None
    if not lead_id:
        lead_id = bitrix.create_lead(contact, msg)

    task_id = None
    if not (duplicate.duplicate and settings.bitrix_duplicate_skip_project_task):
        task_id = bitrix.create_task(contact, msg, lead_id=lead_id)

    bitrix_lead_link = bitrix.build_lead_link(lead_id)
    bitrix_task_link = bitrix.build_task_link(task_id)

    telegram_sent = False
    if not (duplicate.duplicate and settings.lead_telegram_skip_duplicates):
        telegram_sent = TelegramService(settings).send_lead(contact, msg, bitrix_lead_link, bitrix_task_link)

    db.upsert_conversation(
        msg.igsid,
        username=msg.username,
        full_name=msg.full_name,
        phone=contact.phone,
        contact_found=1,
        bitrix_lead_id=lead_id,
        bitrix_task_id=task_id,
        telegram_sent=1 if telegram_sent else 0,
        target_detected=1 if msg.target.detected else 0,
        target_name=msg.target.name,
    )
    if contact.phone and (lead_id or task_id or telegram_sent):
        db.add_sent_lead(contact.phone, msg.igsid, lead_id, task_id)
    log.info("Lead processed for igsid=%s phone=%s lead=%s task=%s telegram=%s", msg.igsid, contact.phone, lead_id, task_id, telegram_sent)


def maybe_send_template(settings: Settings, db: Database, instagram: InstagramService, msg: IncomingMessage) -> None:

    if not settings.contact_template.strip():
        log.info("Instagram auto-reply disabled because CONTACT_TEMPLATE is empty")
        return

    row = db.get_conversation(msg.igsid)
    if not row:
        row = db.upsert_conversation(msg.igsid)
    if row["manual_outgoing_detected"]:
        log.info("Template skipped because manual outgoing was detected for igsid=%s", msg.igsid)
        return
    sent_at = parse_iso(row["template_sent_at"])
    if row["template_sent"] and sent_at:
        age = (parse_iso(utc_now_iso()) - sent_at).total_seconds() if parse_iso(utc_now_iso()) else 0
        if age < settings.min_template_resend_seconds:
            log.info("Template already sent recently for igsid=%s", msg.igsid)
            return
    if instagram.send_message(msg.igsid, settings.contact_template):
        db.upsert_conversation(msg.igsid, template_sent=1, template_sent_at=utc_now_iso())
