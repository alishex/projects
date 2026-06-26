# ALLMAX Telethon Community Agent

Telegram DM (shaxsiy xabar) kanalida ALLMAX mijozlari bilan avtomatik suhbat olib boruvchi AI agent. Claude AI yordamida savollarga javob beradi, stok tekshiradi, buyurtmalarni qayta ishlaydi va Bitrix24 CRM ga lead qo'shadi.

---

## Arxitektura

```
main_ready_project.pyw       # Asosiy Telethon event loop + DM handler
community_agent.py           # Claude API bilan ishlovchi AI agent
media_handler.py             # Rasm/audio/video tahlili (Whisper + base64)
moysklad.py                  # MoySklad stok API (showroom filtri, 10 daqiqa cache)
analytics/
  telegram_dm_log.sqlite3    # DM tarixini yozib boruvchi analytics DB
  media_cache.sqlite3        # Transkriptsiya natijalarini keshlash (message_id asosida)
  analytics.db               # Umumiy analytics
```

---

## Imkoniyatlar

- **Claude AI auto-reply** — barcha DM larga ish vaqtida (09:00–22:00 UTC+5) avtomatik javob
- **Stok tekshirish** — MoySklad showroom ombori bo'yicha real-vaqt stok (60 sek cache)
- **BTS yetkazib berish** — 14 viloyat, 100+ tuman bo'yicha yetkazib berish qoplamasini tekshirish
- **Rasm tahlili** — mijoz yuborgan mahsulot rasmini Claude vision orqali taniy oladi
- **Ovoz/video transkriptsiya** — faster-whisper `base` model, auto-unload (10 daqiqa inactivity)
- **Buyurtma yakunlash** — `order_complete` tool-call orqali CRM ga lead yozadi
- **Kundalik hisobot** — har kuni 00:00 UZT da guruhlarga contact statistikasini yuboradi
- **Human handoff** — `needs_human` tool-call orqali operator guruhiga yo'naltiradi

---

## Texnologiyalar

| Kutubxona | Maqsad |
|-----------|--------|
| `telethon` | Telegram MTProto API (user account) |
| `anthropic` | Claude claude-opus-4-8 AI modeli |
| `faster-whisper` | Ovoz → matn transkriptsiya |
| `requests` | Bitrix24 REST API |
| `sqlite3` | Analytics va media cache |

---

## O'rnatish

```bash
cd /opt/AllmaxProjects/allmax_telethon
python -m venv venv
source venv/bin/activate
pip install telethon anthropic faster-whisper requests python-dotenv
```

---

## .env sozlash

```env
# Telegram
API_ID=...                       # my.telegram.org dan
API_HASH=...
SESSION_NAME=allmax_cm_session

# AI
ANTHROPIC_API_KEY=sk-ant-...

# MoySklad
MOYSKLAD_TOKEN=...

# Bitrix24
BITRIX24_WEBHOOK_URL=https://allmax.bitrix24.kz/rest/1/.../

# Community agent sozlamalari
COMMUNITY_WORK_START=9           # ish boshlanishi (soat, UTC+5)
COMMUNITY_WORK_END=22            # ish tugashi
COMMUNITY_ADDRESS=Toshkent sh., Bunyodkor Savdo Majmuasi ...
COMMUNITY_PHONE=+998 78 555 31 31

# Guruh IDlar (Telegram)
LEAD_GROUP_ID=-100...            # CRM lead xabarlari guruhi
OPERATOR_GROUP_ID=-100...        # Operator handoff guruhi
REPORT_GROUP_ID=-100...          # Kundalik hisobot guruhi
```

---

## Ishga tushirish

```bash
source venv/bin/activate
python main_ready_project.pyw
```

Birinchi ishga tushirishda Telegram autentifikatsiya so'raldi (telefon raqam + kod). Session `allmax_cm_session.session` faylida saqlanadi.

---

## systemd (server)

```
/etc/systemd/system/allmax-telethon.service
```

```bash
systemctl status allmax-telethon
journalctl -u allmax-telethon -f
systemctl restart allmax-telethon
```

---

## Whisper model xotira optimallashtirish

`media_handler.py` da lazy-load + auto-unload mexanizmi ishlatiladi:
- Model faqat birinchi ovoz xabar kelganda yuklanadi (`base` model ~150MB)
- 10 daqiqa ovoz kelmasa model xotiradan tushiriladi (`gc.collect()`)
- Bu `allmax_telethon` ning RAM sarfini ~300MB kamaytiradi

---

## RAM sarfi

| Holat | RAM |
|-------|-----|
| Whisper yuklanmagan | ~800 MB |
| Whisper `base` yuklangan | ~1.1 GB |
| Whisper `small` (eski) | ~1.5 GB |

---

## Muhim eslatmalar

- `allmax_cm_session.session` va `.env` fayllarini **hech qachon** git ga push qilmang
- Claude API kredit balansini doimo kuzatib turing — tugasa barcha DM larga "xatolik" xabari ketadi
- MoySklad token tugasa stok tekshirish ishlashni to'xtatadi (fallback: "mavjudligi noaniq" deydi)
