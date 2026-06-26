# Instagram DM → Bitrix24 CRM / Project → Telegram Lead Notification Bot

Bu loyiha Instagram Direct xabarlarini Meta Webhook orqali qabul qiladi, mijoz xabaridan ism va telefon raqamni ajratadi, SQLite bazada conversation state saqlaydi, Bitrix24 CRM lead yaratadi, kerak bo‘lsa Bitrix24 Project/Zadachi ichida task ochadi va Telegram guruhga yangi lead haqida HTML formatdagi xabar yuboradi.

## 1. Loyiha nima qiladi

Zanjir quyidagicha ishlaydi:

`Instagram DM → Meta Webhook → FastAPI → Regex/OpenAI parser → SQLite → Bitrix24 CRM Lead → Bitrix24 Task → Telegram Lead Group`

Agar mijoz ism va telefon yozmagan bo‘lsa, bot Instagram DM ichida quyidagi shablonni yuboradi:

> Murojatingiz qabul qilindi. Batafsil ma’lumot berishimiz uchun ism va raqamingizni yozib qoldiring. +998 78 555 31 31 raqamidan sizga bog‘lanamiz.

Bot mijoz bilan uzoq suhbat qilmaydi. OpenAI faqat ism va telefon ajratish uchun ishlatiladi.

## 2. Kerakli narsalar

- Python 3.11+
- Meta Developer App
- Instagram Professional/Business account
- Meta webhook uchun public HTTPS URL
- Bitrix24 inbound webhook
- Telegram bot token va guruh chat ID
- OpenAI API key

## 3. `.env` sozlash

Avval `.env.example` faylidan `.env` yarating:

```bash
cp .env.example .env
```

Asosiy to‘ldiriladigan joylar:

```env
META_VERIFY_TOKEN=your_custom_verify_token
META_APP_SECRET=your_meta_app_secret
META_IG_USER_ACCESS_TOKEN=your_instagram_user_access_token
META_IG_BUSINESS_ID=your_instagram_business_id
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-5.5-mini
BITRIX_WEBHOOK_URL=https://yourdomain.bitrix24.kz/rest/USER_ID/WEBHOOK_CODE
BITRIX_ASSIGNED_BY_ID=63
BITRIX_PROJECT_GROUP_ID=15
BITRIX_PROJECT_RESPONSIBLE_ID=63
LEAD_TELEGRAM_BOT_TOKEN=your_telegram_bot_token
LEAD_TELEGRAM_CHAT_ID=-100xxxxxxxxxx
```

Hech qachon real tokenlarni kod ichiga yozmang. `.env` `.gitignore` ichida turadi.

## 4. Instagram Login mode sozlash

```env
META_API_MODE=instagram_login
META_IG_USER_ACCESS_TOKEN=...
META_IG_BUSINESS_ID=...
```

Bu rejimda Instagram access token orqali Instagram Business account nomidan DM yuboriladi.

## 5. Facebook Page mode sozlash

```env
META_API_MODE=facebook_page
META_PAGE_ACCESS_TOKEN=...
META_PAGE_ID=...
META_IG_BUSINESS_ID=...
```

Agar `META_IG_BUSINESS_ID` bo‘sh bo‘lsa, dastur Facebook Page orqali Instagram Business ID topishga urinadi.

## 6. Meta webhook URL ulash

Server public HTTPS URL olgandan keyin Meta Developer panelida webhook callback URL quyidagicha bo‘ladi:

```text
https://your-domain.com/webhook
```

Verify token sifatida `.env` ichidagi `META_VERIFY_TOKEN` qiymatini kiriting.

POST webhook requestlarida `X-Hub-Signature-256` tekshiriladi. `META_APP_SECRET` to‘g‘ri bo‘lishi kerak.

## 7. Bitrix24 webhook olish

Bitrix24 ichida Developer resources / Incoming webhook orqali webhook yarating. Kerakli scope/huquqlar:

- CRM lead yaratish va qidirish
- Task yaratish

`.env` ichiga quyidagicha qo‘ying:

```env
BITRIX_WEBHOOK_URL=https://yourdomain.bitrix24.kz/rest/USER_ID/WEBHOOK_CODE
```

Dastur `crm.lead.add`, `crm.lead.list`, `crm.status.list`, `crm.duplicate.findbycomm`, `tasks.task.add` metodlarini ishlatadi.

## 8. Telegram bot token olish

1. Telegramda `@BotFather` orqali bot yarating.
2. Bot tokenni oling.
3. Botni lead guruhga admin sifatida qo‘shing.
4. Guruh chat ID ni oling.
5. `.env` ichiga kiriting:

```env
LEAD_TELEGRAM_BOT_TOKEN=...
LEAD_TELEGRAM_CHAT_ID=-100xxxxxxxxxx
```

## 9. Lokal ishga tushirish

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Windows:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

## 10. VPS’da ishga tushirish

1. Loyihani VPS ga yuklang.
2. `.env` faylini to‘ldiring.
3. `python run.py` bilan test qiling.
4. Production uchun systemd, Supervisor yoki Docker Compose ishlating.
5. Nginx orqali HTTPS reverse proxy ulang.

## 11. Docker orqali ishga tushirish

```bash
cp .env.example .env
# .env ni to‘ldiring
docker compose up -d --build
```

Loglar:

```bash
docker compose logs -f
```

## 12. Ngrok/cloudflared bilan test qilish

Lokal server:

```bash
python run.py
```

Ngrok:

```bash
ngrok http 8000
```

Webhook URL:

```text
https://xxxx.ngrok-free.app/webhook
```

## 13. Endpointlar

- `GET /` — service status
- `GET /health` — health check
- `GET /webhook` — Meta verify
- `POST /webhook` — Instagram DM webhook receiver

## 14. Dublikat logikasi

Dublikat tekshiruvi uch qatlamda ishlaydi:

1. `processed_events` — bir xil webhook event qayta ishlanmasin.
2. `sent_leads` va `conversations` — bir xil telefon qayta lead bo‘lmasin.
3. Bitrix24 duplicate check — CRM ichida telefon bo‘yicha oldingi lead qidiriladi.

Agar dublikat bo‘lsa:

```env
BITRIX_DUPLICATE_SKIP_CRM_LEAD=true
BITRIX_DUPLICATE_SKIP_PROJECT_TASK=true
LEAD_TELEGRAM_SKIP_DUPLICATES=true
```

bo‘lsa, yangi lead/task/xabar yuborilmaydi.

## 15. Target/reklama logikasi

Dastur payload ichidan quyidagilarni tekshiradi:

- `referral`
- `ad_id`
- `ad_title`
- `source`
- `postback`
- `metadata`
- keywordlar: `target,reklama,ads,ad,instagram target`

Target aniqlansa:

- `target_detected=true`
- Telegramda 🎯 target qatori chiqadi
- Bitrix lead target statusga tushadi
- Bitrix task target stagega tushishi mumkin

## 16. Ko‘p uchraydigan xatolar

**403 Invalid signature**  
`META_APP_SECRET` noto‘g‘ri yoki `X-Hub-Signature-256` kelmayapti.

**Instagram template yuborilmadi**  
`META_IG_BUSINESS_ID` yoki access token noto‘g‘ri.

**Bitrix lead ochilmadi**  
Webhook URL, CRM huquqlari yoki status ID tekshiring.

**Telegram xabar bormadi**  
Bot guruhga qo‘shilganini, adminligini va chat ID to‘g‘riligini tekshiring.

## 17. Troubleshooting

Loglar:

```bash
tail -f logs/app.log
tail -f logs/error.log
```

Testlar:

```bash
pytest
```

SQLite fayl:

```text
data/instagram_dm_bot.sqlite3
```

Agar webhook test qilayotganda signature yo‘q bo‘lsa, lokal test uchun `META_APP_SECRET=replace_me` qoldirilsa verification bypass qilinadi. Productionda esa real secret majburiy.
