from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .bitrix import bitrix_client
from .config import settings
from .database import get_db
from .lead_utils import lead_id_from_item
from .processor import lead_processor

logger = logging.getLogger(__name__)


class Poller:
    def __init__(self) -> None:
        self.db = get_db()
        self.first_run = True

    async def run_once(self) -> None:
        """Backup polling. In realtime mode, first run sets baseline and skips old leads."""
        try:
            leads = await bitrix_client.list_recent_leads(limit=settings.poll_lookback_limit)
            ids: list[int] = []
            by_id = {}
            for item in leads:
                lead_id = lead_id_from_item(item)
                if lead_id is None:
                    continue
                ids.append(lead_id)
                by_id[lead_id] = item

            ids = sorted(set(ids))
            if not ids:
                logger.info("Polling: lead topilmadi")
                await lead_processor.process_pending()
                return

            latest_id = max(ids)
            checkpoint = self.db.get_realtime_checkpoint()
            logger.info("Polling: oxirgi leadlar topildi: %s | checkpoint=%s", ids, checkpoint)

            # SAFE first launch: existing Bitrix leads are baseline, not new notifications.
            if self.first_run and settings.realtime_only_mode and not settings.poll_send_unknown_on_start:
                if checkpoint == 0:
                    self.db.set_realtime_checkpoint(latest_id)
                    checkpoint = latest_id
                    logger.info("Realtime baseline o'rnatildi. Eski leadlar yuborilmaydi. checkpoint=%s", checkpoint)

                skipped_count = self.db.skip_pending_up_to(checkpoint)
                if skipped_count:
                    logger.info("Realtime baseline: eski pending/failed leadlar skipped qilindi: %s", skipped_count)

                for lead_id in ids:
                    if lead_id <= checkpoint and self.db.get_status(lead_id) is None:
                        self.db.mark_skipped(lead_id, "realtime_first_run_skip", by_id.get(lead_id))
                self.first_run = False
                await lead_processor.process_pending()
                return

            await lead_processor.process_pending()

            checkpoint = self.db.get_realtime_checkpoint()
            for lead_id in ids:
                status = self.db.get_status(lead_id)
                if status in {"sent", "skipped"}:
                    continue
                if settings.realtime_only_mode and lead_id <= checkpoint:
                    self.db.mark_skipped(lead_id, "old_polling", by_id.get(lead_id))
                    logger.info("Realtime mode: eski polling lead skipped: lead_id=%s checkpoint=%s", lead_id, checkpoint)
                    continue

                created = await lead_processor.enqueue_lead(lead_id, "polling", by_id.get(lead_id))
                if created or status in {"pending", "failed"}:
                    await lead_processor.process_lead(lead_id, source="polling")

            self.first_run = False
        except Exception as exc:
            logger.exception("Polling xatoligi: %s", exc)


poller = Poller()
scheduler = AsyncIOScheduler(timezone=settings.timezone)


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        poller.run_once,
        trigger=IntervalTrigger(seconds=settings.poll_interval_seconds),
        id="bitrix_lead_backup_polling",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Scheduler ishga tushdi. interval=%s sec", settings.poll_interval_seconds)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler to'xtatildi")
