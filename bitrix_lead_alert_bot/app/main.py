from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .config import settings
from .database import get_db
from .lead_utils import extract_lead_id_from_payload
from .logger import setup_logging
from .processor import lead_processor
from .scheduler import poller, start_scheduler, stop_scheduler

setup_logging()
logger = logging.getLogger(__name__)


async def read_payload(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
        return data if isinstance(data, dict) else {"payload": data}

    # Bitrix outgoing webhooks usually send application/x-www-form-urlencoded.
    try:
        form = await request.form()
        return dict(form)
    except Exception:
        body = await request.body()
        return {"raw": body.decode("utf-8", errors="ignore")}


def check_secret(request: Request, payload: dict[str, Any]) -> None:
    expected = settings.webhook_secret
    if not expected:
        return

    provided = (
        request.query_params.get("secret")
        or request.headers.get("x-webhook-secret")
        or str(payload.get("secret", ""))
    )
    if provided != expected:
        raise HTTPException(status_code=403, detail="Webhook secret noto'g'ri")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate()
    get_db().init()
    start_scheduler()
    # Run one immediate poll on startup to process pending leads and catch fresh missed leads.
    await poller.run_once()
    yield
    stop_scheduler()


app = FastAPI(
    title="Bitrix24 Lead Alert Telegram Bot",
    description="Bitrix24 yangi leadlarini Telegram guruhga mas’ul odamni mention qilib yuboradi.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "stats": get_db().stats()}


@app.post("/bitrix/lead")
async def bitrix_lead_webhook(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    payload = await read_payload(request)
    check_secret(request, payload)

    lead_id = extract_lead_id_from_payload(payload)
    if lead_id is None:
        logger.warning("Webhook keldi, lekin lead ID topilmadi. payload=%s", payload)
        raise HTTPException(status_code=400, detail="Lead ID topilmadi")

    await lead_processor.enqueue_lead(lead_id, "webhook", payload)
    background_tasks.add_task(lead_processor.process_lead, lead_id, "webhook")
    return JSONResponse({"ok": True, "lead_id": lead_id, "status": "queued"})


@app.post("/manual/lead/{lead_id}")
async def manual_lead(lead_id: int, request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    payload = await read_payload(request)
    check_secret(request, payload)

    await lead_processor.enqueue_lead(lead_id, "manual", payload)
    background_tasks.add_task(lead_processor.process_lead, lead_id, "manual")
    return JSONResponse({"ok": True, "lead_id": lead_id, "status": "queued"})


@app.post("/admin/retry-pending")
async def retry_pending(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    payload = await read_payload(request)
    check_secret(request, payload)

    background_tasks.add_task(lead_processor.process_pending)
    return JSONResponse({"ok": True, "status": "retry_started"})
