# ALLMAX Instagram Community Agent

Instagram DM (to'g'ridan-to'g'ri xabar) kanalida ALLMAX mijozlari bilan Claude AI yordamida avtomatik suhbat olib boruvchi webhook-based agent. FastAPI + Meta Webhook orqali ishlaydi.

---

## Arxitektura

```
run.py                               # Entrypoint — uvicorn ishga tushuradi
app/
  main.py                            # FastAPI app yaratish + startup
  config.py                          # .env sozlamalari (pydantic Settings)
  database.py                        # SQLite: suhbat tarixi, lead holati
  models.py                          # IncomingMessage pydantic modeli
  logger.py                          # Rotating file + console logger
  routes/
    webhook.py                       # POST /webhook — Meta webhook handler
  services/
    community_agent.py               # Claude AI agent (tool-use: check_stock, order_complete, needs_human)
    instagram_service.py             # Meta Graph API: xabar o'qish va yuborish
    moysklad.py                      # MoySklad stok tekshiruvi (showroom filtri)
    bitrix_service.py                # Bitrix24 CRM: lead yaratish, duplicate tekshirish
    duplicate_service.py             # Bitrix24 orqali duplicate lead filteri
    telegram_service.py              # Operator guruhiga handoff xabari
    meta_signature.py                # Meta webhook HMAC imzo tekshiruvi
    target_detector.py               # Webhook payload dan maqsad IG akkaunt aniqlash
    openai_parser.py                 # (Legacy) kontakt parser — Claude ga ko'chirilmoqda
  utils/
    phone.py                         # Telefon raqam normalizatsiya
    text.py                          # Matn tozalash yordamchilari
    time_utils.py                    # UTC vaqt yordamchilari
    retry.py                         # Eksponensial retry dekorator
  workers/
    conversation_sync.py             # Fon worker: suhbat tarixini DB ga sinxronlash
data/
  instagram_dm_bot.sqlite3           # SQLite bazasi
logs/
  app.log, error.log                 # Rotating loglar
tests/
  test_phone.py, test_duplicate.py   # Unit testlar
```

---

## Imkoniyatlar

- **Claude AI auto-reply** — ish vaqtida (09:00–22:00 UTC+5) kelgan barcha DM larga avtomatik javob
- **Stok tekshirish** — MoySklad showroom bo'yicha real-vaqt stok so'rovi (`check_stock` tool)
- **BTS yetkazib berish** — 14 viloyat bo'yicha `bts_check` tool orqali qoplama tekshirish
- **Lead yaratish** — `order_complete` tool-call → Bitrix24 CRM da yangi lead ochiladi
- **Duplicate filtri** — Bitrix24 orqali bir xil telefon/email ga ikki marta lead ochilmaydi
- **Human handoff** — `needs_human` signal → operator Telegram guruhiga yo'naltiradi
- **Meta webhook xavfsizligi** — HMAC-SHA256 imzo tekshiruvi (`META_APP_SECRET` orqali)

---

## Texnologiyalar

| Kutubxona | Maqsad |
|-----------|--------|
| `fastapi` | Webhook HTTP server |
| `uvicorn` | ASGI runner |
| `anthropic` | Claude claude-opus-4-8 AI modeli |
| `httpx` | Meta Graph API va Bitrix24 ga HTTP so'rovlar |
| `pydantic` | Config va model validatsiya |
| `sqlite3` | Suhbat tarixi va state saqlash |

---

## O'rnatish

```bash
cd /opt/AllmaxProjects/allmax_instagram_agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env ni to'ldiring (quyida ko'rsatilgan)
```

---

## .env sozlash

```env
# Server
APP_HOST=0.0.0.0
APP_PORT=8002
APP_ENV=production

# Meta / Instagram
META_VERIFY_TOKEN=...            # Webhook tekshirish uchun o'z tokeningiz
META_APP_SECRET=...              # Meta App Secret (HMAC imzo tekshiruvi uchun)
META_PAGE_ACCESS_TOKEN=...       # Facebook Page Access Token (uzun muddatli)
META_PAGE_ID=...                 # Facebook Page ID
META_IG_BUSINESS_ID=...          # Instagram Business Account ID

# AI
ANTHROPIC_API_KEY=sk-ant-...

# MoySklad
MOYSKLAD_TOKEN=...

# Bitrix24
BITRIX24_WEBHOOK_URL=https://allmax.bitrix24.kz/rest/1/.../

# Telegram (operator handoff)
TELEGRAM_BOT_TOKEN=...
TELEGRAM_OPERATOR_GROUP_ID=-100...

# Community agent
COMMUNITY_WORK_START=9
COMMUNITY_WORK_END=22
COMMUNITY_ADDRESS=Toshkent sh., Bunyodkor Savdo Majmuasi ...
COMMUNITY_PHONE=+998 78 555 31 31
```

---

## Ishga tushirish

```bash
source venv/bin/activate
python run.py
```

Server `0.0.0.0:8002` portida ishlaydi. Meta Webhook URL: `https://allmax.tizm.uz/instagram/webhook`

---

## systemd (server)

```
/etc/systemd/system/allmax-instagram-agent.service
```

```bash
systemctl status allmax-instagram-agent
journalctl -u allmax-instagram-agent -f
systemctl restart allmax-instagram-agent
```

---

## Nginx konfiguratsiya

`/etc/nginx/...` da proxy: `allmax.tizm.uz/instagram/` → `localhost:8002/`

---

## Meta Webhook sozlash

1. Meta Developer Console → App → Webhooks
2. Callback URL: `https://allmax.tizm.uz/instagram/webhook`
3. Verify Token: `.env` dagi `META_VERIFY_TOKEN` bilan bir xil
4. Subscribe: `messages`, `messaging_postbacks`

---

## Muhim eslatmalar

- Meta Page Access Token 60 kunda muddati o'tadi — uzun muddatli token oling
- `META_IG_BUSINESS_ID` noto'g'ri bo'lsa xabar yuborishda `400 Bad Request` chiqadi
- Claude API kredit balansini kuzatib turing — tugasa barcha DM larga fallback javob ketadi
- `.env` faylini **hech qachon** git ga push qilmang
