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

BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
CHAT_ID         = os.getenv("CHAT_ID", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
TZ_OFFSET       = int(os.getenv("TIMEZONE_OFFSET", "5"))

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
        log.warning("Telegram stats xatosi: %s", exc)
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
        return {"total": row[0] or 0, "contacts": row[1] or 0, "targets": row[2] or 0}
    except Exception as exc:
        log.warning("Instagram stats xatosi: %s", exc)
        return {"total": 0, "contacts": 0, "targets": 0}


async def send_message(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json={"chat_id": CHAT_ID, "text": text})
        if resp.status_code != 200:
            log.warning("Telegram send xatosi: %s %s", resp.status_code, resp.text[:200])


def build_report_with_claude(tg: dict, ig: dict, start_local: datetime, end_local: datetime) -> str:
    months_uz = [
        "", "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
        "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
    ]
    days_uz = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]

    date_str = f"{start_local.day} {months_uz[start_local.month]} {start_local.year}"
    day_str  = days_uz[start_local.weekday()]
    start_str = start_local.strftime("%H:%M")
    end_str   = end_local.strftime("%H:%M")

    total_all = tg["unique_users"] + ig["total"]

    if tg["unique_users"] > ig["total"]:
        top_channel = "Telegram"
    elif ig["total"] > tg["unique_users"]:
        top_channel = "Instagram"
    else:
        top_channel = None

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""Quyidagi raqamlar asosida ALLMAX kompaniyasi uchun soatlik hisobot yoz.

Hisobot uchun ma'lumotlar:
  Sana: {date_str}, {day_str}
  Soat: {start_str} dan {end_str} gacha (UTC+5, Toshkent vaqti)

  Telegram DM:
    Yangi murojaat (unique odamlar): {tg["unique_users"]} ta
    Jami xabarlar: {tg["total_messages"]} ta

  Instagram DM:
    Yangi suhbatlar: {ig["total"]} ta
    Kontakt (ism va telefon) qoldirdi: {ig["contacts"]} ta
    Target reklama orqali keldi: {ig["targets"]} ta

  Jami murojaat: {total_all} ta
  Eng faol kanal: {top_channel if top_channel else "Teng"}

Qoidalar (MUHIM):
  1. Faqat Telegram oddiy matn formati ishlatilsin
  2. Hech qanday # (xeshteg), * (yulduzcha), _ (pastki chiziq) ISHLATMA
  3. Chiroyli ko'rinish uchun faqat EMOJI va oddiy harflar ishlatilsin
  4. O'zbek tilida yoz
  5. Professional va qisqa bo'lsin
  6. Agar jami 0 bo'lsa: "Bu soatda murojaat kelmadi" deb yoz, lekin baribir chiroyli qilib
  7. Boshida katta sarlavha bo'lsin, keyin kanallar bo'yicha ma'lumot, oxirida jami
  8. Har bir bo'lim orasida bo'sh qator bo'lsin"""

    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return (resp.content[0].text or "").strip()


async def run_report():
    now_utc   = datetime.now(timezone.utc)
    local_off = timedelta(hours=TZ_OFFSET)
    now_local = now_utc + local_off

    end_local   = now_local.replace(minute=0, second=0, microsecond=0)
    start_local = end_local - timedelta(hours=1)

    end_utc   = end_local   - local_off
    start_utc = start_local - local_off

    log.info("Hisobot tayyorlanmoqda: %s — %s", start_local.strftime("%H:%M"), end_local.strftime("%H:%M"))

    tg = get_telegram_stats(start_utc, end_utc)
    ig = get_instagram_stats(start_utc, end_utc)

    log.info("Telegram: %s users, %s msgs | Instagram: %s convs", tg["unique_users"], tg["total_messages"], ig["total"])

    try:
        text = build_report_with_claude(tg, ig, start_local, end_local)
    except Exception as exc:
        log.error("Claude xatosi: %s", exc)
        text = (
            f"Soatlik hisobot\n"
            f"{start_local.strftime('%H:%M')} — {end_local.strftime('%H:%M')}\n\n"
            f"Telegram: {tg['unique_users']} ta murojaat\n"
            f"Instagram: {ig['total']} ta murojaat\n"
            f"Jami: {tg['unique_users'] + ig['total']} ta"
        )

    await send_message(text)
    log.info("Hisobot yuborildi")


async def main():
    log.info("Analytics report bot ishga tushmoqda...")

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(run_report, "cron", minute=0)
    scheduler.start()

    log.info("Scheduler yoqildi — har soat :00 da hisobot yuboriladi")

    # Birinchi testni darhol yuborish uchun:
    # await run_report()

    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
