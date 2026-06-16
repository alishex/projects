import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

BOT_TOKEN         = os.getenv("BOT_TOKEN", "")
CHAT_ID           = os.getenv("CHAT_ID", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL   = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
TZ_OFFSET         = int(os.getenv("TIMEZONE_OFFSET", "5"))

TELEGRAM_DB  = Path(os.getenv("TELEGRAM_DB",  "/opt/AllmaxProjects/allmax_telethon/analytics/telegram_dm_log.sqlite3"))
INSTAGRAM_DB = Path(os.getenv("INSTAGRAM_DB", "/opt/AllmaxProjects/instagram_bitrix_dm_lead_bot/data/instagram_dm_bot.sqlite3"))


def get_telegram_stats(start_utc: datetime, end_utc: datetime) -> dict:
    if not TELEGRAM_DB.exists():
        return {"unique_users": 0, "total_messages": 0}
    try:
        con = sqlite3.connect(TELEGRAM_DB)
        s = start_utc.strftime("%Y-%m-%d %H:%M:%S")
        e = end_utc.strftime("%Y-%m-%d %H:%M:%S")
        cur = con.execute(
            "SELECT COUNT(DISTINCT user_id), COUNT(*) FROM dm_events WHERE ts >= ? AND ts < ?",
            (s, e),
        )
        row = cur.fetchone()
        con.close()
        return {"unique_users": row[0] or 0, "total_messages": row[1] or 0}
    except Exception as exc:
        log.warning("Telegram SQLite xatosi: %s", exc)
        return {"unique_users": 0, "total_messages": 0}


def get_instagram_stats(start_utc: datetime, end_utc: datetime) -> dict:
    if not INSTAGRAM_DB.exists():
        return {"total": 0, "contacts": 0, "targets": 0}
    try:
        con = sqlite3.connect(INSTAGRAM_DB)
        s = start_utc.strftime("%Y-%m-%d %H:%M:%S")
        e = end_utc.strftime("%Y-%m-%d %H:%M:%S")
        cur = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(contact_found),0), COALESCE(SUM(target_detected),0) "
            "FROM conversations WHERE datetime(created_at) >= datetime(?) AND datetime(created_at) < datetime(?)",
            (s, e),
        )
        row = cur.fetchone()
        con.close()
        log.info("Instagram stats: total=%s contacts=%s targets=%s", row[0], row[1], row[2])
        return {"total": row[0] or 0, "contacts": row[1] or 0, "targets": row[2] or 0}
    except Exception as exc:
        log.warning("Instagram SQLite xatosi: %s", exc)
        return {"total": 0, "contacts": 0, "targets": 0}


async def send_message(text: str) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json={"chat_id": CHAT_ID, "text": text})
        if resp.status_code != 200:
            log.warning("Telegram send xatosi: %s", resp.text[:200])
            return False
        return True


def build_report(tg: dict, ig: dict, start_local: datetime, end_local: datetime) -> str:
    months_uz = ["", "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
                 "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"]
    days_uz = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]

    date_str  = f"{start_local.day} {months_uz[start_local.month]} {start_local.year}"
    day_str   = days_uz[start_local.weekday()]
    start_str = start_local.strftime("%H:%M")
    end_str   = end_local.strftime("%H:%M")

    tg_unique   = tg.get("unique_users", 0)
    tg_total    = tg.get("total_messages", 0)
    ig_convs    = ig.get("total", 0)
    ig_contacts = ig.get("contacts", 0)
    ig_targets  = ig.get("targets", 0)

    total_all = tg_unique + ig_convs
    top = "Telegram" if tg_unique > ig_convs else ("Instagram" if ig_convs > tg_unique else "Teng")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""Quyidagi raqamlar asosida ALLMAX kompaniyasi uchun soatlik hisobot yoz.

Sana: {date_str}, {day_str}
Soat: {start_str} dan {end_str} gacha (UTC+5, Toshkent vaqti)

Telegram DM:
  Yangi murojaat (unique odamlar): {tg_unique} ta
  Jami xabarlar: {tg_total} ta

Instagram DM:
  Yangi suhbatlar: {ig_convs} ta
  Kontakt (ism/telefon) qoldirdi: {ig_contacts} ta
  Target reklama orqali keldi: {ig_targets} ta

Jami murojaat: {total_all} ta
Eng faol kanal: {top}

Qoidalar:
1. Faqat oddiy Telegram matn formati
2. Hech qanday # * _ belgi ishlatma
3. Faqat EMOJI va oddiy harflar
4. O'zbek tilida, professional va qisqa
5. Agar 0 bo'lsa ham chiroyli qilib yoz
6. Boshida sarlavha, keyin kanallar, oxirida jami
7. Har bo'lim orasida bo'sh qator"""

    try:
        resp = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        return (resp.content[0].text or "").strip()
    except Exception as exc:
        log.error("Claude xatosi: %s", exc)
        return (
            f"Soatlik hisobot {start_str} — {end_str}\n\n"
            f"Telegram: {tg_unique} ta\nInstagram: {ig_convs} ta\nJami: {total_all} ta"
        )


async def run_report():
    local_off   = timedelta(hours=TZ_OFFSET)
    now_utc     = datetime.now(timezone.utc)
    now_local   = now_utc + local_off
    end_local   = now_local.replace(minute=0, second=0, microsecond=0)
    start_local = end_local - timedelta(hours=1)
    end_utc     = end_local - local_off
    start_utc   = start_local - local_off

    log.info("Hisobot: %s — %s", start_local.strftime("%H:%M"), end_local.strftime("%H:%M"))

    tg = get_telegram_stats(start_utc, end_utc)
    ig = get_instagram_stats(start_utc, end_utc)

    log.info("TG: unique=%s msgs=%s | IG: convs=%s contacts=%s targets=%s",
             tg["unique_users"], tg["total_messages"],
             ig["total"], ig.get("contacts", 0), ig.get("targets", 0))

    text = build_report(tg, ig, start_local, end_local)
    await send_message(text)
    log.info("Hisobot yuborildi")


async def main():
    log.info("Analytics report bot ishga tushmoqda...")
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(run_report, "cron", minute=0)
    scheduler.start()
    log.info("Scheduler yoqildi — har soat :00 da hisobot yuboriladi")
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
