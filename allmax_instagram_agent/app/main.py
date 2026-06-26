from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.database import Database
from app.logger import setup_logging
from app.routes.webhook import router as webhook_router
from app.workers.conversation_sync import conversation_sync_loop

settings = get_settings()
setup_logging(settings.log_level, settings.secret_values)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database(settings.sqlite_path)
    db.init()
    app.state.db = db
    sync_task: asyncio.Task | None = None
    if settings.enable_conversation_sync:
        sync_task = asyncio.create_task(conversation_sync_loop(settings, db))
    log.info("Application started")
    try:
        yield
    finally:
        if sync_task:
            sync_task.cancel()
            try:
                await sync_task
            except asyncio.CancelledError:
                pass
        log.info("Application stopped")


app = FastAPI(
    title="Instagram DM -> Bitrix24/Telegram Lead Bot",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(webhook_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "instagram_bitrix_dm_lead_bot", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
