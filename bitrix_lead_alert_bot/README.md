# Bitrix24 Lead Alert Telegram Bot

Bu bot Bitrix24 CRM’da **faqat yangi lead real-time tushganda** Telegram guruhga ogohlantirish yuboradi va mas’ul odamni mention qiladi.

Bot ishonchli ishlashi uchun 2 qatlamli qilingan:

1. **Webhook** — Bitrix24’dan lead tushishi bilan darhol signal oladi.
2. **Backup polling** — har 1 daqiqada Bitrix24’dan oxirgi leadlarni tekshiradi, lekin eski leadlarni yubormaydi.

> Ushbu versiyada `REALTIME_ONLY_MODE=true` va `POLL_SEND_UNKNOWN_ON_START=false` default bo‘ldi. Ya’ni bot birinchi ishga tushganda Bitrix24’dagi eski leadlarni “yangi lead” deb yubormaydi.

---

## 1. Papka tarkibi

```text
bitrix_lead_alert_bot/
├── app/
│   ├── main.py              # FastAPI endpointlar
│   ├── bitrix.py            # Bitrix24 REST API client
│   ├── telegram_client.py   # Telegram Bot API client + 429 rate limit himoyasi
│   ├── processor.py         # Leadni yuborish/retry logikasi
│   ├── scheduler.py         # Realtime-only backup polling
│   ├── database.py          # SQLite baza + realtime checkpoint
│   ├── config.py            # .env sozlamalar
│   └── lead_utils.py        # Lead/contact parsing va xabar formatlash
├── scripts/
│   └── get_chat_id.py       # Telegram chat_id aniqlash
├── systemd/
│   └── bitrix-lead-alert.service
├── data/
├── logs/
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── run.py
```

---

## 2. Yangilangan versiyada tuzatilgan narsalar

- Eski leadlarni yangi lead deb yuborish to‘xtatildi.
- Birinchi ishga tushganda bot eng oxirgi Bitrix24 lead ID’ni baseline/checkpoint qilib oladi.
- Backup polling endi faqat checkpointdan keyin tushgan leadlarni yuboradi.
- Oldingi bazada qolib ketgan `pending/failed` eski leadlar checkpointgacha bo‘lsa `skipped` qilinadi.
- Telegram `429 Too Many Requests` holatida bot `retry_after` vaqtini kutadi.
- Xabarlar orasiga kichik pauza qo‘shildi: `TELEGRAM_MIN_DELAY_SECONDS=1.2`.
- Lead ichida ism bo‘lmasa, bot bog‘langan contactni olib, ism/telefon/emailni contactdan chiqarishga urinadi.

---

## 3. Kerakli narsalar

- Python 3.11+
- Telegram bot token
- Telegram guruh chat ID
- Mention qilinadigan odamning Telegram user ID
- Bitrix24 incoming webhook URL
- Bitrix24 outgoing webhook event: `onCrmLeadAdd`
- Production uchun domain + SSL tavsiya qilinadi

---

## 4. Telegram bot tayyorlash

1. Telegram’da `@BotFather` orqali bot yarating.
2. Tokenni oling.
3. Botni kerakli Telegram guruhga qo‘shing.
4. Botga guruhga xabar yozish huquqini bering.
5. Guruhga biror test xabar yozing.

Chat ID olish:

```bash
cp .env.example .env
nano .env
```

Avval faqat `TELEGRAM_BOT_TOKEN` ni to‘ldiring.

Keyin:

```bash
python scripts/get_chat_id.py
```

Natijada guruh `chat_id` chiqadi. Odatda supergroup ID `-100...` bilan boshlanadi.

Mas’ul odamning Telegram user ID sini ham shu skriptdan ko‘rishingiz mumkin. U odam guruhga xabar yozgan yoki botga private `/start` yuborgan bo‘lishi kerak.

---

## 5. Bitrix24 webhook tayyorlash

### Incoming webhook

Bitrix24 ichida incoming webhook yarating va CRM o‘qish huquqini bering.

`.env` ichiga shunday qo‘ying:

```env
BITRIX_WEBHOOK_BASE_URL=https://yourcompany.bitrix24.kz/rest/1/xxxxxxxxxxxxxxxx/
BITRIX_PORTAL_URL=https://yourcompany.bitrix24.kz
```

### Outgoing webhook

Bitrix24’da outgoing webhook yarating:

- Event: `onCrmLeadAdd`
- Handler URL:

```text
https://SIZNING-DOMAIN.uz/bitrix/lead?secret=CHANGE_ME_LONG_RANDOM
```

Agar serverda hali domain/SSL bo‘lmasa, vaqtincha test uchun `ngrok` ishlatish mumkin. Production uchun domain + SSL tavsiya qilinadi.

---

## 6. .env to‘ldirish

`.env.example` ni `.env` qilib nusxalang:

```bash
cp .env.example .env
nano .env
```

Asosiy sozlamalar:

```env
TELEGRAM_BOT_TOKEN=123456789:AA_example_token_here
TELEGRAM_CHAT_ID=-1001234567890
TELEGRAM_MENTION_USER_ID=123456789
TELEGRAM_MENTION_NAME=Muhammad Ali

BITRIX_WEBHOOK_BASE_URL=https://yourcompany.bitrix24.kz/rest/1/xxxxxxxxxxxxxxxx/
BITRIX_PORTAL_URL=https://yourcompany.bitrix24.kz

WEBHOOK_SECRET=CHANGE_ME_LONG_RANDOM

APP_HOST=0.0.0.0
APP_PORT=8000
TIMEZONE=Asia/Tashkent

POLL_INTERVAL_SECONDS=60
POLL_LOOKBACK_LIMIT=50
RETRY_MAX_ATTEMPTS=5

REALTIME_ONLY_MODE=true
POLL_SEND_UNKNOWN_ON_START=false
TELEGRAM_MIN_DELAY_SECONDS=1.2
```

`WEBHOOK_SECRET` uzun random qiymat bo‘lsin. Bitrix outgoing webhook URL oxirida ham shu secret turishi kerak.

---

## 7. Oddiy ishga tushirish

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Tekshirish:

```bash
curl http://127.0.0.1:8000/health
```

Manual test faqat tekshirish uchun:

```bash
curl -X POST "http://127.0.0.1:8000/manual/lead/123?secret=CHANGE_ME_LONG_RANDOM"
```

`manual` endpoint realtime filterdan mustasno. Shuning uchun eski lead bilan manual test qilsangiz, u baribir Telegramga ketishi mumkin. Real ishlashda Bitrix24 `onCrmLeadAdd` webhookidan foydalaning.

---

## 8. Hozirgi eski bazani tozalash kerakmi?

Majburiy emas. Yangilangan kod birinchi ishga tushganda checkpoint o‘rnatadi va checkpointgacha bo‘lgan eski `pending/failed` leadlarni `skipped` qiladi.

Lekin toza boshlamoqchi bo‘lsangiz:

```bash
rm -f data/bot.db data/bot.db-wal data/bot.db-shm
```

Keyin botni qayta ishga tushiring:

```bash
python run.py
```

Birinchi startda bot eski leadlarni yubormaydi. Faqat shu startdan keyin Bitrix24’da yangi lead tushsa xabar yuboradi.

---

## 9. Docker orqali ishga tushirish

```bash
docker compose up -d --build
```

Log ko‘rish:

```bash
docker logs -f bitrix-lead-alert-bot
```

---

## 10. systemd orqali 24/7 ishlatish

Loyihani serverga `/opt/bitrix_lead_alert_bot` papkasiga joylang.

```bash
cd /opt/bitrix_lead_alert_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Service faylni ko‘chiring:

```bash
sudo cp systemd/bitrix-lead-alert.service /etc/systemd/system/bitrix-lead-alert.service
sudo systemctl daemon-reload
sudo systemctl enable bitrix-lead-alert
sudo systemctl start bitrix-lead-alert
```

Status:

```bash
sudo systemctl status bitrix-lead-alert
```

Log:

```bash
journalctl -u bitrix-lead-alert -f
```

---

## 11. Nginx reverse proxy namunasi

```nginx
server {
    server_name SIZNING-DOMAIN.uz;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

SSL uchun:

```bash
sudo certbot --nginx -d SIZNING-DOMAIN.uz
```

---

## 12. Ishlash logikasi

### Birinchi start

1. Bot Bitrix24’dan oxirgi leadlarni ko‘radi.
2. Eng katta lead ID’ni checkpoint qilib oladi.
3. Shu ID va undan kichik leadlar eski deb hisoblanadi.
4. Ularga Telegram xabar yuborilmaydi.

### Webhook kelganda

1. Bitrix24 `/bitrix/lead` endpointiga lead ID yuboradi.
2. Bot secretni tekshiradi.
3. Lead ID’ni ajratadi.
4. Leadni SQLite bazaga `pending` status bilan yozadi.
5. Bitrix24’dan lead ma’lumotlarini oladi.
6. Lead contactga bog‘langan bo‘lsa, contact ma’lumotini ham olib ismni chiqarishga urinadi.
7. Telegram guruhga xabar yuboradi.
8. Muvaffaqiyatli bo‘lsa `sent` status qiladi.

### Webhook kelmasa

Har `POLL_INTERVAL_SECONDS` sekundda bot Bitrix24’dan oxirgi leadlarni oladi. Faqat checkpointdan keyingi leadlar Telegramga yuboriladi.

### Telegram xatolik bersa

Bot `RETRY_MAX_ATTEMPTS` marta qayta urinadi. Agar Telegram `429 Too Many Requests` qaytarsa, bot `retry_after` vaqtini kutadi.

---

## 13. Telegram xabar namunasi

```text
🆕 Yangi lead tushdi

👤 Mas’ul: Muhammad Ali
🆔 Lead ID: 1842
📌 Nomi: Instagram Lead
🙋 Mijoz ismi: Sardor
📞 Telefon: +998901234567
✉️ Email: —
📍 Manba: WEBFORM
📊 Status: NEW
👨‍💼 Bitrix mas’ul ID: 1
🕒 Vaqt: 20.05.2026 14:35

🔗 Bitrix24’da ochish
```

Telegramda mas’ul odam ID orqali mention qilinadi.

---

## 14. Muhim eslatmalar

- Bot guruhga xabar yozish huquqiga ega bo‘lishi shart.
- Mention ishlashi uchun `TELEGRAM_MENTION_USER_ID` to‘g‘ri bo‘lishi kerak.
- Bitrix24 incoming webhook CRM lead/contactlarni o‘qiy olishi kerak.
- Agar Bitrix24 lead ichida ham, bog‘langan contact ichida ham ism yo‘q bo‘lsa, bot ismni `—` qilib chiqaradi. Telefonni ism sifatida ko‘rsatmaydi.
- `WEBHOOK_SECRET`, Telegram bot token va Bitrix webhook URL’ni hech kimga bermang.
- Productionda server uchun domain + SSL ishlating.
- `.env` faylni GitHub yoki boshqa ommaviy joyga yuklamang.
