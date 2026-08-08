# ALLMAX Projects

**ALLMAX** (erkaklar kiyim-kechak chakana savdo brendi, Fix Price uslubida) kompaniyasining barcha avtomatlashtirish loyihalari — Telegram botlar, Instagram integratsiya, CRM alertlar, AI yordamchilar, HR tizimi va ichki dashboard.

**Server:** DigitalOcean VPS "tools" — Ubuntu 24.04 — `209.38.239.245` — 4 vCPU / 8 GB RAM (`s-4vcpu-8gb`, 2026-07-20da kattalashtirilgan) — disk 50GB (~25% band)
**AI:** Anthropic Claude `claude-opus-4-8` (asosiy model, deyarli barcha loyihalarda) — ba'zi eski loyihalarda `claude-sonnet-4-6` fallback sifatida kodda qoldirilgan
**GitHub:** [alishex/projects](https://github.com/alishex/projects) (**public repo**) — push 2026-08-08dan beri ishlayapti (yangi fine-grained PAT, avvalgi token 07-18dan o'lik edi)
**Bu hujjat oxirgi to'liq qayta tekshiruv:** 2026-08-08, barcha loyihalar jonli kodni o'qib, systemd holatini tekshirib yozilgan (eski hujjat iyun oyidan beri yangilanmagan va ko'p joyda noto'g'ri edi — pastdagi "Xavfsizlik va tuzatishlar" bo'limiga qarang)

---

## ⚠️ Xavfsizlik ogohlantirishlari

Bu hujjatni yangilash paytida o'tkazilgan chuqur tekshiruvda 3 ta xavfsizlik muammosi topildi. Ikkitasi **shu kuni tuzatildi** (git tarixidagi kod endi toza), lekin **haqiqiy kalitlarni almashtirish faqat sizning qo'lingizda**:

1. **`allmax_dashboard/main.py`da login/parol ochiq matnda yozilgan edi** (git orqali kuzatiladigan faylda). ✅ Tuzatildi — endi `.env` fayliga ko'chirildi (git'ga kirmaydi), parolning o'zi o'zgarmadi, dashboard qayta tekshirilib ishlayotgani tasdiqlandi. ⚠️ Eski qiymat hali git tarixida qoladi (`git log -p` orqali ko'rinadi) — **agar to'liq xavfsiz bo'lishni istasangiz, parolni almashtirish tavsiya etiladi**, aytsangiz yordam beraman.
2. **`bitrix_lead_alert_bot/.env.example` va `marketing_task_control_bot/.env.example` fayllarida HAQIQIY Telegram bot tokenlari va Bitrix24 webhook manzili yozilgan edi** — bu fayllar **public GitHub repo**siga (`alishex/projects`) push qilingan, ya'ni kimdir bu qiymatlarni ko'rgan bo'lishi mumkin. ✅ Tuzatildi — fayllar placeholder qiymatlarga almashtirildi. ⚠️ **Tavsiya: ikkala botning Telegram tokenini @BotFather orqali va Bitrix24 webhookni Bitrix24 panelidan qayta yarating** — eski qiymatlar hali git tarixida ochiq turibdi. Buni ham xohlasangiz, GitHub token yaratishda qilganimdek qadam-baqadam yordam bera olaman.
3. **`bitrix_lead_alert_bot`ning "real-time webhook"i aslida tashqaridan yetib bo'lmaydi** (8000-port UFW'da yopiq, nginx'da ham marshrut yo'q) — bot kod darajasida webhook qabul qiluvchi bo'lsa-da, amalda faqat **har 60 soniyada backup polling** orqali ishlayapti. Bu ishonchli ishlayapti (1198/1198 lead muvaffaqiyatli yetkazilgan), shunchaki "real-time" degani unchalik to'g'ri emas — atigi ~1 daqiqagacha kechikish bor. Agar chinakam real-time kerak bo'lsa, nginx+UFW'da atayin ochish kerak bo'ladi (xavfsizlik nuqtai nazaridan ongli qaror talab qiladi, shuning uchun o'zim hal qilmadim).

Bulardan tashqari, `allmax_dashboard`dagi "Tizim holati" paneli (Faol/Kredit belgilari) **jonli emas — qattiq yozilgan (hardcoded) va hech qachon yangilanmaydi**, faqat 4 ta statistika kartasi, grafik va kontaktlar ro'yxati haqiqatan ham jonli. Bu xavfsizlik muammosi emas, shunchaki chalg'ituvchi — bilib qo'yish kifoya.

---

## Loyihalar ro'yxati

| # | Loyiha | Holat | Tavsif | Port | RAM (jonli, 08-08) |
|---|---|---|---|---|---|
| 1 | [allmax_dashboard](#1-allmax_dashboard) | ✅ Faol | Telethon agent statistikasi uchun ichki web dashboard | 8080 (ichki) | ~35 MB |
| 2 | [allmax_food_order_bot](#2-allmax_food_order_bot) | ✅ Faol | 7 bo'lim uchun kunlik ovqat buyurtma + Owner Panel | — | ~144 MB |
| 3 | [bitrix_lead_alert_bot](#3-bitrix_lead_alert_bot) | ✅ Faol | Bitrix24 yangi lead → Telegram guruh alert (amalda polling) | 8000 (tashqi yopiq) | ~87 MB |
| 4 | [feedback_bot](#4-feedback_bot) | ✅ Faol | Mijoz fikr-mulohaza (reyting, media, telefon) yig'ish | — | ~114 MB |
| 5 | [food_control_bot](#5-food_control_bot) | ✅ Faol | Marketing bo'limi ovqat nazorati (12 xodim faol) | — | ~137 MB |
| 6 | [marketing_task_control_bot](#6-marketing_task_control_bot) | ✅ Faol | Vazifalar + Eisenhower matritsa grafik hisobot | — | ~92 MB |
| 7 | [allmax_telethon](#7-allmax_telethon) | ⏸ To'xtatilgan (07-24) | ALLMAX biznes akkaunt — Community Agent (savdo/support) | — | — |
| 8 | [telegram_ai_assistant](#8-telegram_ai_assistant) | ⏸ To'xtatilgan (07-08) | Egasining shaxsiy akkaunti uchun Claude yordamchi | — | — |
| 9 | [allmax_instagram_agent](#9-allmax_instagram_agent) | ⏸ To'xtatilgan (06-28) | Instagram DM Community Agent (telethon'ning egizagi) | 8002 (410 qaytadi) | — |
| 10 | [allmax_hr_bot](#10-allmax_hr_bot) | ⏸ To'xtatilgan (06-20) | To'liq HR pipeline: ariza → AI intervyu → onboarding | — | — |
| 11 | [allmax_ai_assistant](#11-allmax_ai_assistant) | 🚫 Hech qachon ishga tushirilmagan | Tashlab qo'yilgan prototip (telegram_ai_assistant fork'i) | — | — |
| — | [instagram_bitrix_dm_lead_bot](#ochirilgan-loyihalar-tarixi) | 🗑 To'liq o'chirilgan (06-26) | Eski Instagram bot — allmax_instagram_agent bilan almashtirilgan | — | — |
| 12 | [narzullo_portfolio](#12-narzullo_portfolio) | ✅ Faol (shaxsiy) | **ALLMAXga aloqasi yo'q** — server egasining shaxsiy sayti | 443 (static) | — |

> **Jami RAM (6 faol bot):** ~610 MB / 8 GB. Server umumiy: ~1.2–2.1 GB ishlatilmoqda (vaqt bo'yicha o'zgaradi), disk 25% (12G/48G).

---

# Faol loyihalar

## 1. allmax_dashboard

> Boshqa loyiha (`allmax_telethon`)ning SQLite bazasini o'qiydigan, real-vaqt statistika ko'rsatuvchi ichki web dashboard. O'zi hech qanday yozish amalini bajarmaydi — faqat ko'rsatish uchun.

### Nima qiladi

Yagona maqsadli FastAPI ilova: `allmax_telethon/analytics/telegram_dm_log.sqlite3` bazasini to'g'ridan-to'g'ri (ORM'siz, xom `sqlite3` bilan) o'qib, ALLMAX xodimlariga Telegram Community Agentning faoliyatini ko'rsatadi.

**Sahifalar/route'lar:**

| Route | Metod | Vazifasi |
|---|---|---|
| `/login` | GET/POST | Login sahifasi — email/parol tekshirib `sid` cookie qo'yadi (httponly, 7 kun) |
| `/logout` | GET | Sessiyani tozalaydi |
| `/` | GET | Dashboard SPA (kirilmagan bo'lsa `/login`ga yo'naltiradi) |
| `/api/stats` | GET | Bugun/hafta/oy foydalanuvchi va xabar soni, jami leadlar, "operator kerak" soni |
| `/api/daily` | GET | Oxirgi N kunlik (7/14/30) statistikasi — bar-grafik uchun |
| `/api/contacts` | GET | Oxirgi N ta kontakt (ism, username, mavzu, "necha vaqt oldin") |

Frontend — vanilla JS + Tailwind (CDN) + Chart.js (CDN), build qadam yo'q, Jinja2 ishlatilmaydi (`FileResponse` orqali statik HTML). Har 30 soniyada avto-yangilanadi. `docs_url=None` — Swagger/ReDoc atayin o'chirilgan.

**Muhim:** "Tizim holati" paneli (allmax-telethon/Anthropic/MoySklad/Bitrix24 belgilari) **statik/qattiq yozilgan — hech qanday backendga ulanmagan**, doim bir xil holatni ko'rsatadi. Faqat 4 ta stat-karta, grafik va kontaktlar ro'yxati jonli.

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `fastapi` | Web server |
| `uvicorn[standard]` | ASGI server |
| `python-multipart` | Login form parsing |
| `aiofiles` | Statik fayllarga async kirish |
| `python-dotenv` | **(2026-08-08 qo'shildi)** `.env`dan login/parol o'qish |

### Konfiguratsiya

**2026-08-08gacha `.env` fayli umuman yo'q edi** — EMAIL/PASSWORD `main.py` ichida ochiq matnda edi (xavfsizlik bo'limiga qarang). Endi:
```env
DASHBOARD_EMAIL=...
DASHBOARD_PASSWORD=...
```

### Fayllar

```
allmax_dashboard/
├── main.py            — Butun FastAPI ilova (auth + API), ~160 qator
├── requirements.txt
├── .env               — (2026-08-08dan, gitignored)
└── static/
    ├── index.html      — SPA: stat kartalar, grafik, kontaktlar, "tizim holati"
    └── login.html       — Login forma
```

### Systemd va tarmoq

```
service: allmax-dashboard
port:    8080 (faqat localhost — UFW tashqaridan yopgan)
nginx:   https://allmax.tizm.uz/dashboard/  →  proxy_pass http://127.0.0.1:8080/
```

---

## 2. allmax_food_order_bot

> ALLMAXning 7 ta bo'limi uchun kunlik tushlik/kechki ovqat buyurtmasini yig'adigan va to'liq **kod o'zgartirmasdan** (DB-based) boshqariladigan Owner Panelga ega Telegram bot.

### Nima qiladi

**A) Bo'lim admini / o'rinbosar oqimi:**
1. Har kuni belgilangan vaqtda (standart **17:00**, DB orqali o'zgartiriladi) scheduler har bo'lim adminiga ertangi menyuni (2 haftalik aylanma sikldan) va "📝 Buyurtma berish" tugmasini yuboradi
2. Admin tushlik va kechki ovqat porsiya sonini kiritadi → tasdiqlaydi → `department_orders` jadvaliga yoziladi
3. `/edit` — tasdiqlangan buyurtmani qayta tahrirlash
4. **O'rinbosarga yuborish** — admin kunlik so'rovni o'rinbosarga bir martalik topshirishi mumkin
5. **"Boshliqlar" bo'limi "fixed"** — DBda qayd etilgan doimiy son (hozir 3/2), admin kerak emas, scheduler avtomatik yozadi
6. Doimiy tugmalar: **"🍽 Yakuniy hisobot"** (video-note bilan qoldiq ovqat isboti, guruhga yuboriladi), **"💬 Fikr-mulohaza"** (barcha Ownerlarga yuboriladi)
7. Bir foydalanuvchi uchun parallel buyurtma/hisobot/feedback boshlanishini bloklaydigan "conflict guard" + har user uchun alohida `asyncio.Lock`

**B) Owner Panel (`/owner`, faqat `OWNER_IDS`, hozir 2 ta owner):**
- 📊 Ertangi holat — qaysi bo'lim javob berdi/bermadi, kim va qachon tasdiqladi
- ✏️ Buyurtma kiritish — istalgan bo'lim uchun to'g'ridan-to'g'ri override
- 🏢 Bo'limlar — to'liq CRUD: qo'shish/o'chirish, admin/o'rinbosar tayinlash, "kunlik so'ralsin" ↔ "fixed" rejim almashtirish
- 👑 Ownerlar — qo'shish/o'chirish (oxirgi ownerni o'chirishga yo'l qo'ymaydi)
- 📝 Menyu — 14 kunlik siklni ko'rish/tahrirlash
- 🔄 Sikl — "bugun siklning qaysi kuni" ni bir bosishda qayta belgilash
- 🕐 Vaqtlar — so'rov va hisobot vaqtini o'zgartirish (APScheduler `reschedule_job` — restart shart emas)
- 📋 **Hisobotni hozir olish** (eng yangi funksiya, 2026-08-07 qo'shilgan)

**C) Rejalashtirilgan vazifalar** (`Asia/Tashkent`, `misfire_grace_time=3600`):
- `send_daily_poll` — standart 17:00, jonli logda tasdiqlangan: "7/7 bo'limga yuborildi"
- `send_owner_report` — kodda 18:00, lekin **DBda hozir 20:00ga sozlangan** — "2/2 ownerga yuborildi"

Real hajmlar (08-06/07): WMS 7/7, Marketing 12/9, Umumiy1 6/6, Umumiy2 3/2, Moliya 13/10, Savdo 17/10 + Boshliqlar avtomatik 3/2 — barcha 7 bo'lim barqaror ishlayapti.

**Muhim dizayn qarori:** `.env`dagi qiymatlar faqat birinchi ishga tushirishda "seed" sifatida ishlatiladi — shundan keyin **baza yagona haqiqat manbai**, `.env`ni o'zgartirish hech narsaga ta'sir qilmaydi, hammasi Owner Panel orqali. Bu ataylab shunday qilingan (kodda izoh bilan tasdiqlangan).

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram==3.17.0` | Telegram bot |
| `apscheduler==3.10.4` | Kunlik so'rov + hisobot |
| `aiosqlite==0.20.0` | Async SQLite |
| `pytz==2024.2` | Vaqt zonasi |

### Konfiguratsiya (faqat birinchi ishga tushirish uchun "seed")

```env
BOT_TOKEN, OWNER_ID_1, OWNER_ID_2, GROUP_ID,
ADMIN_BOSHLIQLAR, ADMIN_UMUMIY1, ADMIN_UMUMIY2, ADMIN_MOLIYA, ADMIN_MARKETING, ADMIN_WMS, ADMIN_SAVDO,
FIXED_BOSHLIQLAR_MEAL1, FIXED_BOSHLIQLAR_MEAL2,
DEPUTY_BOSHLIQLAR, DEPUTY_UMUMIY1, DEPUTY_UMUMIY2, DEPUTY_MOLIYA, DEPUTY_MARKETING, DEPUTY_WMS, DEPUTY_SAVDO,
ANCHOR_DATE, ANCHOR_INDEX, DB_PATH
```

### Fayllar

```
allmax_food_order_bot/
├── main.py                — Bot ishga tushirish, ~35 qator
├── data/orders.db          — Jonli SQLite (5 jadval: menu, settings, department_orders, departments, owners)
└── app/
    ├── config.py            — .env seed + runtime DB-config
    ├── database.py          — Barcha CRUD, avtomigratsiya (~370 qator)
    ├── keyboards.py         — Barcha klaviaturalar (~370 qator)
    ├── scheduler.py         — Kunlik so'rov + hisobot job'lari
    ├── states.py
    ├── handlers/admin.py    — Admin/o'rinbosar oqimi (~560 qator)
    ├── handlers/owner.py    — To'liq Owner Panel (~680 qator)
    └── services/menu_service.py, report_service.py
```
~2385 qator ilova kodi — kichik skript emas, to'liq ichki tizim.

### Systemd

```
service: allmax-food-order-bot
bot:     @food_control_rBot (id 8877062313)
port:    yo'q (long-polling)
```

---

## 3. bitrix_lead_alert_bot

> Bitrix24 CRMga yangi lead tushganda Telegram guruhiga xabar yuboradi. **Amalda faqat 60 soniyalik polling orqali ishlaydi** — real-time webhook yo'li kod darajasida bor, lekin tashqaridan yetib bo'lmaydi (yuqoridagi xavfsizlik bo'limiga qarang).

### Nima qiladi

Kod hujjatlar taxmin qilganidan ancha puxtaroq — har lead uchun to'liq holat mashinasi (`pending → sent/skipped/failed`, urinishlar soni, oxirgi xato, WAL rejimi):

1. **Backup polling** — har `POLL_INTERVAL_SECONDS` (60s) da Bitrix24 `crm.item.list` (yoki eski `crm.lead.list` fallback) so'raladi
2. **Realtime-baseline himoyasi** — birinchi ishga tushganda saqlangan checkpointga ishonmasdan, Bitrix'dagi eng katta lead ID'ni "boshlanish nuqtasi" deb oladi — eski leadlar hech qachon xato alert qilinmaydi
3. **Kontakt boyitish** — lead'ga bog'langan contact bo'lsa, ism/telefon/email shu yerdan olinadi
4. **Qayta urinish** — `RETRY_MAX_ATTEMPTS` (5) marta, ortib boruvchi kechikish bilan, har lead uchun alohida `asyncio.Lock`
5. Telegram tomonda `TELEGRAM_MIN_DELAY_SECONDS` bilan tezlik cheklovi + 429 `retry_after` bilan ishlash

**Haqiqiy endpoint'lar** (eski hujjatda noto'g'ri `/webhook` deb yozilgan edi):
```
GET  /health                     — {"ok":true,"stats":{"sent":N,"skipped":N}}
POST /bitrix/lead                — webhook qabul qiluvchi (form yoki JSON)
POST /manual/lead/{lead_id}       — qo'lda test uchun (realtime filtrni chetlab o'tadi)
POST /admin/retry-pending
```

Jonli holat (08-08 tekshiruvda `/health` orqali): **1198 ta lead muvaffaqiyatli yuborilgan, 50 ta o'tkazib yuborilgan (eski baseline), 0 xato**.

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `fastapi` | Webhook server |
| `uvicorn[standard]` | ASGI |
| `apscheduler` | Backup polling |
| `httpx` | Bitrix24 + Telegram API |
| `pydantic` | Validatsiya |

### Konfiguratsiya

```env
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_MENTION_USER_ID, TELEGRAM_MENTION_NAME,
BITRIX_WEBHOOK_BASE_URL, BITRIX_PORTAL_URL, WEBHOOK_SECRET,
APP_HOST, APP_PORT, TIMEZONE, LOG_LEVEL, DATABASE_PATH, LOG_FILE,
POLL_INTERVAL_SECONDS, POLL_LOOKBACK_LIMIT, RETRY_MAX_ATTEMPTS, RETRY_BASE_DELAY_SECONDS,
REQUEST_TIMEOUT_SECONDS, REALTIME_ONLY_MODE, POLL_SEND_UNKNOWN_ON_START, TELEGRAM_MIN_DELAY_SECONDS
```
*(`.env.example` 2026-08-08gacha haqiqiy qiymatlar bilan git'da edi — endi placeholder, yuqoridagi xavfsizlik bo'limiga qarang.)*

### Fayllar

```
bitrix_lead_alert_bot/
├── run.py, Dockerfile, docker-compose.yml   (Docker fayllar bor, lekin production systemd+venv orqali ishlaydi)
├── data/bot.db, logs/bot.log(.1-.5)
├── scripts/get_chat_id.py
└── app/
    ├── main.py, bitrix.py, telegram_client.py, processor.py
    ├── scheduler.py, database.py, config.py, lead_utils.py, logger.py
```

### Systemd

```
service: bitrix-lead-alert-bot
port:    8000 (localhost, tashqaridan YOPIQ — UFW + nginx marshrutsiz)
```

---

## 4. feedback_bot

> Mijozlardan 1–5 baho + matn/media/telefon yig'uvchi bot. Har mijoz uchun yig'ma (rolling) xulosa xabarini admin guruhida yangilab turadi.

### Nima qiladi

Oqim (eski hujjatda "reyting birinchi" deb noto'g'ri yozilgan edi — **aslida aksincha**):
1. `/start` → "📝 Fikr qoldirish" (reply-klaviatura)
2. Foydalanuvchi **avval kontent yuboradi** — matn (min 5 belgi) yoki rasm/video/video-note/ovoz
3. Keyin **1–5 yulduz** so'raladi (reply-klaviatura tugmalari, inline emas)
4. Keyin **telefon raqami** so'raladi (ixtiyoriy — "share contact" yoki "⏭ O'tkazib yuborish")
5. Yakunda barcha ma'lumot birlashtirilib `ADMIN_CHAT_ID`ga yuboriladi (media guruh + alohida ovoz/video-note xabarlari)
6. **Hujjatlashtirilmagan xususiyat:** har foydalanuvchi tarixi saqlanadi (oxirgi 50 matn, 10 media) — yangi fikr kelganda bot **admin guruhidagi eski xabarini o'chirib, yangilangan yig'ma xulosani qayta yuboradi** (xabarlar oqimi emas, bitta yangilanuvchi karta)
7. Saqlash atomik (`feedbacks.json.tmp` → `os.replace()`, `asyncio.Lock` ostida)

Jonli holat: 10 ta noyob foydalanuvchi fikr qoldirgan (5★×6, 2★×3, 1★×1).

**Tuzatilgan tarixiy bug (commit `ca3f35b`, 06-17):** "O'tkazib yuborish" tugmasi qayrilgan tirnoq (’) ishlatgan, handler esa oddiy tirnoqni (') tekshirgan — mos kelmagani uchun tugma ishlamas edi. Hozir ikkalasi ham to'g'ri, tasdiqlangan.

### Texnologiyalar

`aiogram==3.7.0`, `python-dotenv==1.0.1`

### Konfiguratsiya

```env
BOT_TOKEN, ADMIN_CHAT_ID
```

### Fayllar

```
feedback_bot/
├── bot.py, config.py, states.py
├── handlers/  start.py, feedback.py
├── keyboards/ menu.py, rating.py
└── storage/   feedbacks.json
```

### Systemd

```
service: feedback-bot
bot:     @allmax_feedback_bot (id 8629969732)
```

---

## 5. food_control_bot

> Marketing bo'limi uchun ovqat buyurtma + eyilganini video orqali tasdiqlash boti, to'liq no-code admin panelga ega.

### Nima qiladi

1. **Menyu yuborish** (scheduler, DB-konfiguratsiya qilinadigan vaqt, **jonlida hozir 13:30** Toshkent — eski hujjatda 17:30 deb yozilgan edi, bu eskirgan) — 14 kunlik aylanma sikldan ertangi menyu, inline "1-ovqat/2-ovqat" tugmalari bilan yuboriladi
2. Foydalanuvchi ha/yo'q tanlaydi, tasdiqlaydi → agar **barcha** faol foydalanuvchilar javob bersa, admin avtomatik to'liq hisobotni oladi
3. **Ovqat eyilgani isboti** — "ha" deganlar uchun "🍽 Ovqat hisoboti" tugmasi, qaysi ovqatligini tanlab **video-note** (dumaloq video) yuboradi — bu admin va guruhga yuboriladi
4. **Yakuniy hisobot** (DB-konfiguratsiya, hozir 22:00) — kunlik to'liq hisob-kitob (buyurtma/tugatilgan/javob bermagan, "qoldiq ovqat" soni)

**Admin imkoniyatlari — ikkita parallel interfeys:**
- Eski matn buyruqlari: `/set_users`, `/set_group`, `/set_menu`, `/set_cycle`, `/report`, `/today`, `/tomorrow`, `/reset_day`
- **Yangi `/admin` inline panel** (commit `aa9bf55`, 07-13) — bugungi holat, xodimlarni birma-bir qo'shish/o'chirish (12 ta cheklov olib tashlangan), buyurtmalarni ko'rish, **har xodimning buyurtmasini admin to'g'ridan-to'g'ri o'zgartirishi**, menyuni tahrirlash, sikl qayta belgilash, **jadval vaqtlarini jonli o'zgartirish** (restart shart emas), ko'p-adminlilik

**Jonli tuzatish (bu tekshiruvda topilgan):** hujjatlarda "13 xodim" deb yozilgan, lekin bazada 13tadan **faqat 12tasi hozir faol** (2tasi admin panel orqali soft-remove qilingan, tarix uchun saqlangan). Haqiqiy faol son: **12**, jonli logda ham tasdiqlangan ("Ertangi menyu yuborildi: 12 foydalanuvchiga").

### Texnologiyalar

`aiogram==3.13.1`, `aiosqlite==0.20.0`, `apscheduler==3.10.4`, `pytz==2024.1`

### Konfiguratsiya

```env
BOT_TOKEN, SUPER_ADMIN_ID, TIMEZONE, DB_PATH, ANCHOR_DATE, ANCHOR_WEEK, ANCHOR_DAY, ANCHOR_INDEX, ADMIN_IDS
```

### Fayllar

```
food_control_bot/
├── main.py, food_control.db
└── app/
    ├── config.py, database.py, keyboards.py, scheduler.py, utils.py
    ├── handlers/  admin.py (847 qator), callbacks.py, user.py
    └── services/  menu_service.py, order_service.py, report_service.py, user_service.py
```

### Systemd

```
service: food-control-bot
bot:     @ovqatnazoratiuzbot (id 8816441483)
```

---

## 6. marketing_task_control_bot

> Marketing jamoasi uchun vazifa berish/nazorat + Eisenhower matritsasi shaklida PNG grafik hisobot.

### Nima qiladi

1. Admin xodimga vazifa yaratadi (matn + qisqa "grafik nomi" + P1–P4 muhimlik)
2. Xodim deadline taklif qiladi → admin tasdiqlaydi yoki o'zgartiradi → `ACTIVE`
3. **Eslatmalar** — 24 soat, 3 soat, 1 soat qolganda (1 soatlik eslatma adminga ham boradi), har eslatma turi DBda belgilanadi (restart'da qaytalanmaydi)
4. **Muddati o'tsa** — avtomatik `OVERDUE`ga o'tadi, ikkalasiga ham ogohlantirish, grafik qizil rangda "KECHIKKAN" belgisi bilan qayta chiziladi
5. Xodim "yakunlangan" deb belgilaydi → admin o'z vaqtida/kech bajarilgani haqida xabar oladi
6. **Grafik hisobot** (Pillow) — 1890×1063 shablon nusxasidan (asl fayl hech qachon o'zgarmaydi), har vazifa matni tegishli katakka avto word-wrap bilan yoziladi, 5tadan ortiq vazifa bo'lsa qo'shimcha sahifa

Muhimlik hisoblash: statik P1=400...P4=100 ball + muddat yaqinligiga qarab bonus (+80 <24s, +50 <3k, +20 <7k) + kechikkanlarga +1000 jarima. Ruxsat — qattiq allowlist middleware, faqat admin yoki tayinlangan xodim botdan foydalana oladi.

### Texnologiyalar

`aiogram>=3.7,<4`, `aiosqlite`, `apscheduler>=3.10,<4`, `Pillow`, `pytest`/`pytest-asyncio` (2 test fayli bor)

### Konfiguratsiya

```env
BOT_TOKEN, ADMIN_ID, TIMEZONE, DATABASE_PATH, LOG_LEVEL
```
*(`.env.example` 2026-08-08gacha haqiqiy tokenga o'xshash qiymat bilan git'da edi — endi placeholder.)*

### Fayllar

```
marketing_task_control_bot/
├── bot.py, config.py
├── database/  database.py, models.py, repositories.py
├── handlers/  admin, common, employee, graph_reports, settings, task_creation, task_management
├── services/  cleanup_service, matrix_image_service, notification_service, priority_service, reminder_service, task_service
├── middlewares/ auth_middleware.py
├── assets/    toliq_ish_vazifalar_template.png
└── tests/     test_matrix_image_service.py, test_priority_service.py
```

### Systemd

```
service: marketing-task-control-bot
bot:     @allmax_vazifalarbot (id 8061098327)
```

---

# To'xtatilgan loyihalar

*Kod serverda bor, systemd xizmat ham mavjud, lekin hozir `disabled`+`inactive` — qayta yoqish uchun `systemctl enable --now <service>`, lekin pastdagi har bir izohni o'qib chiqing (ba'zilarida qayta yoqishdan oldin tekshirish kerak bo'lgan narsalar bor).*

## 7. allmax_telethon

> ALLMAX biznes Telegram akkaunti (`allmax_cm_session`) nomidan ishlaydigan **Community Agent** — mijozlar bilan avtomatik suhbat, MoySklad stok tekshiruvi, Bitrix24 CRM/Projects integratsiyasi. Eng ko'p ishlab chiqilgan loyiha (30+ commit).

### To'xtatilgan sana va sababi

**2026-07-24, 09:16** — atayin, toza to'xtatish (jurnal: mijoz ovoz xabarini qayta ishlayotgan payti, keyin `systemd[1]: Stopped ... Deactivated successfully`) — halokat emas.

### Nima qiladi

- Telethon orqali ALLMAX akkauntiga kelgan DM'larni (matn/ovoz/video/rasm/GIF/stiker) qabul qiladi, ketma-ket xabarlarni 1.8s burst-collector bilan birlashtiradi
- Claude (`community_agent.py`) oxirgi 30 kunlik tarixni ko'rib javob beradi — til avtomatik aniqlanadi (UZ/RU/EN)
- **Operator ustuvorligi** — inson operator xabar yozsa, agent shu foydalanuvchi uchun jim bo'lib qoladi (jonli logda tasdiqlangan)
- `check_stock` (MoySklad, 600s cache, sinonim/fuzzy qidiruv: "remen"→kamar, "ochki"→ko'zoynak), `order_complete` (Bitrix24 Lead+Project task), `needs_human`, `share_location` — 4 ta Claude tool, agentik loop (maks 4 iteratsiya)
- Ism+telefon aniqlansa, to'liq buyurtma kutmasdan Bitrix24 Project task ochiladi
- Har kuni 00:00 UZTda kunlik hisobot guruhga yuboriladi
- BTS yetkazib berish uchun 14 viloyat/100+ tuman qamrovi kod ichida (taxminiy, izoh bilan belgilangan)
- Ovoz/video: faster-whisper (`base`, `language="uz"`), 10 daqiqa harakatsizlikdan keyin avto-unload (~300MB tejash)

### Texnologiyalar

`telethon`, `anthropic`, `faster-whisper`, `ffmpeg` (OGG/WebM magic-byte aniqlash), `sqlite3`, `requests`
**⚠️ `requirements.txt` bu loyihada YO'Q** — muhitni noldan qayta tiklash uchun jonli venv'dan versiyalarni chiqarish kerak bo'ladi.

### Konfiguratsiya (asosiylari)

```env
TELEGRAM_API_ID, TELEGRAM_API_HASH, PHONE_NUMBER, SESSION_NAME, ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
COMMUNITY_AGENT_ENABLE, COMMUNITY_HISTORY_LIMIT, COMMUNITY_HISTORY_DAYS, COMMUNITY_ADDRESS,
COMMUNITY_WORK_START, COMMUNITY_WORK_END, LEAD_GROUP, MESSAGE_BURST_WINDOW, MAX_BURST_MESSAGES,
MOYSKLAD_TOKEN, BITRIX_ENABLE, BITRIX_WEBHOOK_URL, BITRIX_PROJECT_* (7 ta qo'shimcha)
```
*(To'liq ro'yxat ~30 ta o'zgaruvchi — eng boy konfiguratsiya sirtiga ega loyiha.)*

### Fayllar

```
allmax_telethon/
├── main_ready_project.pyw   — Asosiy, 62KB
├── community_agent.py        — Claude agent, 21KB
├── media_handler.py          — Whisper + vizual, 16KB
├── moysklad.py                — Stok tekshiruv, 7KB
├── allmax_cm_session.session
└── analytics/                 — 4 ta SQLite baza (dm_events, daily_contacts, va h.k.)
```

### Systemd

```
service: allmax-telethon
holat:   disabled, inactive (2026-07-24dan)
```

⚠️ Loyihaning o'zidagi README'da `.env` kalitlari (`API_ID`, `BITRIX24_WEBHOOK_URL`) jonli `.env`dagi haqiqiy nomlardan (`TELEGRAM_API_ID`, `BITRIX_WEBHOOK_URL`) farq qiladi — mahalliy README ham eskirgan.

---

## 8. telegram_ai_assistant

> Egasining **shaxsiy** Telegram akkaunti uchun umumiy maqsadli Claude yordamchisi — erkin tilda topshiriq berasiz, bot Telethon orqali sizning akkountingiz nomidan bajaradi.

### To'xtatilgan sana va sababi

**2026-07-08, 21:36** — bundan oldin **halokatli tsikl** bo'lgan: `RuntimeError: Telegram session topilmadi yoki tasdiqlanmagan` xatosi bilan systemd har ~5 soniyada qayta urinib, jurnal **9462+ marta** qayta ishga tushirishni qayd etgan. Keyin qo'lda to'xtatilgan. Session fayli hozir tekshirilganda (to'g'ridan-to'g'ri sqlite3 orqali) **haqiqatan ham avtorizatsiyadan o'tgan** ko'rinadi — ya'ni kimdir muammoni aniqlagandan keyin login jarayonini qayta bajargan, lekin shundan beri hech qachon qayta ishga tushirilmagan, shuning uchun bugun ham ishlab ketishi 100% kafolatlanmaydi (avval sinab ko'rish tavsiya etiladi).

### Nima qiladi

- Alohida **buyruq boti** (`@Claude_ai_oBot`) orqali OWNER_USER_ID'dan kelgan har qanday xabarni "topshiriq" deb qabul qiladi
- `claude_agent.py` — Claude agentik tool-use loop (maks 25 qadam), 6 ta tool: `list_dialogs`, `get_chat_history`, `search_messages`, `send_message`, `get_chat_info`, `get_current_datetime`
- **Eng boy media pipeline (3 loyiha ichida):** ovoz/video/audio (Whisper), **video** (kadr ajratish + Claude Vision + audio transkript birgalikda), rasm, va **HEIC/HEIF** (iPhone fotolar) — boshqa ikkita o'xshash loyihada bu yo'q
- `file_reader.py` — PDF/Word/Excel/CSV fayllarni o'qib Claude'ga beradi
- Faqat matn/HTML formatida javob beradi (Telegram-xavfsiz teglar, Markdown emas)
- Suhbat tarixi JSON faylda (`conversation_history.json`, 60KB — haqiqiy foydalanish tarixi 06-23gacha)

### Texnologiyalar (`requirements.txt`)

```
telethon==1.36.0
anthropic>=0.40.0
aiogram==3.15.0
python-dotenv==1.1.1
faster-whisper>=1.0.0
```

### Konfiguratsiya

```env
TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, TELEGRAM_SESSION_NAME,
COMMAND_BOT_TOKEN, OWNER_USER_ID, ANTHROPIC_API_KEY, CLAUDE_MODEL,
MAX_AGENT_STEPS, LOG_LEVEL, MAX_TRANSCRIBE_PER_CALL, WHISPER_MODEL_SIZE
```

### Fayllar

```
telegram_ai_assistant/
├── bot.py                — Buyruq bot kirish nuqtasi
├── claude_agent.py        — Tool-use loop + system prompt
├── telegram_client.py     — TelegramToolset (Telethon amallar)
├── media_transcriber.py   — Ovoz/video/rasm/HEIC tushunish
├── file_reader.py         — PDF/Word/Excel/CSV
├── memory_store.py, config.py, login_session.py (bir martalik interaktiv login)
```

### Systemd

```
service: telegram-ai-assistant
bot:     @Claude_ai_oBot
holat:   disabled, inactive (2026-07-08dan)
```

---

## 9. allmax_instagram_agent

> `allmax_telethon`ning Instagram egizagi — Claude AI Community Agent, Meta Webhook orqali Instagram DM'larga javob beradi, MoySklad+Bitrix24 bilan integratsiya. **Eski `instagram_bitrix_dm_lead_bot`ning to'liq qayta yozilgan o'rnini bosuvchisi** (2026-06-26, bir xil commit'da eskisi o'chirilib bu qo'shilgan — pastga qarang).

### To'xtatilgan sana va sababi

**~2026-06-27/28** — kaskad xato: Instagram Graph API xabar yuborishda `400 Bad Request` (token eskirgan) + bir vaqtda Anthropic `"credit balance is too low"` xatosi, keyin qo'lda to'xtatilgan.

### Nima qiladi

- FastAPI + Meta Webhook (`GET /webhook` — tasdiqlash handshake, `POST /webhook` — HMAC-SHA256 imzo tekshiruv bilan)
- Har DM: dublikat tekshiruv (`event_id`) → profil ma'lumot olish → tarix bootstrap → media qayta ishlash (rasm/Reels/video/sticker — Claude Vision yoki matn label) → **Claude Community Agent** javob beradi va Instagramga yuboradi → regex+Claude bilan telefon/ism ajratiladi → Bitrix24 Lead+Project task → Telegram ops guruhiga bildirishnoma
- 3 ta tool: `check_stock`, `order_complete` (9 maydon), `needs_human`
- **Target/reklama aniqlash** — Meta payload'dan ad/referral belgilarni topib, shu orqali kelgan leadlarni alohida Bitrix statusda belgilaydi
- Fon worker (~45s) — Instagram konversatsiyalarini poll qilib, operator qo'lda javob berganini aniqlaydi (operator ustuvorlik patterni, telethon'dagi kabi)

### Nginx marshruti

```nginx
location /instagram/ {
    # allmax_instagram_agent 2026-06-28dan o'chirilgan (8002 tinglamaydi)
    return 410;
}
```
Meta hali obunani bekor qilmagan (kuniga ~40-50K so'rov keladi), lekin server endi statik `410 Gone` qaytaradi — proxy urinishi yo'q, log/CPU yuki yo'q. To'liq to'xtatish faqat Meta App Dashboard orqali, foydalanuvchi tomonidan.

### Texnologiyalar (`requirements.txt`)

```
fastapi==0.115.8, uvicorn[standard]==0.34.0, httpx==0.28.1,
pydantic==2.10.6, anthropic>=0.40.0
```

### Konfiguratsiya (qisqartirilgan — to'liq ro'yxat ~45 ta o'zgaruvchi)

```env
META_API_MODE, META_VERIFY_TOKEN, META_APP_SECRET, META_IG_USER_ACCESS_TOKEN, META_PAGE_ACCESS_TOKEN,
META_IG_BUSINESS_ID, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, BITRIX_* (14 ta), LEAD_TELEGRAM_* (9 ta),
TARGET_VIDEO_*, COMMUNITY_AGENT_ENABLE, COMMUNITY_WORK_START/END, MOYSKLAD_TOKEN
```

### Fayllar

```
allmax_instagram_agent/
├── run.py, Dockerfile, docker-compose.yml (production aslida systemd+venv orqali ishlaydi)
├── README.md / README_RU.md / README_UZ.md
└── app/
    ├── main.py, config.py, database.py, models.py, logger.py
    ├── routes/webhook.py
    ├── services/ community_agent.py, moysklad.py, bitrix_service.py, instagram_service.py,
    │             telegram_service.py, duplicate_service.py, target_detector.py, meta_signature.py,
    │             openai_parser.py  (⚠️ nomi "openai" lekin aslida Anthropic Claude chaqiradi)
    └── workers/conversation_sync.py
```

### Systemd

```
service: allmax-instagram-agent
holat:   disabled, inactive (~2026-06-27/28dan)
```

⚠️ **Qayta yoqishdan oldin:** Instagram access token va Anthropic kredit balansini tekshiring — ikkalasi ham to'xtash sababi edi. Shuningdek `app/main.py`dagi FastAPI title/root endpoint hali eski loyihaning nomini (`instagram_bitrix_dm_lead_bot`) ko'rsatadi — funksional emas, faqat kosmetik.

---

## 10. allmax_hr_bot

> ALLMAX uchun to'liq HR avtomatlashtirish — vakansiya arizasidan yakuniy testgacha, 27 jadvalli baza bilan.

### To'xtatilgan sana

**2026-06-20, 13:03** — qo'lda SIGTERM (halokat emas, jurnalda xato ko'rinmaydi).

### Nima qiladi

1. **Ariza** — til tanlash (UZ/RU) → vakansiyalar ro'yxati → **23 savolli** to'liq anketa (ism, tug'ilgan sana, telefon, viloyat/tuman, oilaviy holat, talaba ma'lumoti, ta'lim, UZ/RU/EN til darajasi, kompyuter savodxonligi, ish jadvali, maosh kutilmasi, manba, kuchli/zaif tomonlar, motivatsiya, ishga chiqish sanasi) → ixtiyoriy **10 tagacha ish tajribasi** yozuvi → rasm → rozilik → **draft-resume** tizimi (tugallanmagan arizani keyin davom ettirish mumkin)
2. **AI intervyu** — vakansiya+reglamentga mos savollar (standart 10 ta) generatsiya qilinadi, javoblar 0–100 ball, `low/medium/excellent` daraja, admin tavsiyasi (`reject/review/invite_interview`) — AI ishlamasa **heuristik zaxira baholovchi** bor, pipeline hech qachon to'xtamaydi
3. **PDF eksport** — har nomzod uchun to'liq dossier (ReportLab), adminlarga avtomatik yuboriladi
4. **Follow-up** — botning o'zi keyinroq "intervyu qanday o'tdi?" deb yozadi, javobni AI tasniflaydi (`accepted/rejected/waiting/unclear`)
5. **7 kunlik onboarding** — aniq **7 kunga taqsimlangan 20 ta dars**, har biridan keyin AI generatsiya qilgan 10 savolli test, <60% yoki >80% natijada adminga avtomatik ogohlantirish, 20-darsdan keyin 30 savolli yakuniy test
6. **Clockster integratsiyasi** — faqat stajirovka+yakuniy test tugagandan KEYIN yoqiladi, xodimlarni ism bo'yicha fuzzy-matching bilan bog'laydi
7. **Excel eksport** — to'liq pipeline jadvali (openpyxl)
8. **Dinamik admin panel** (`dynamic_admin.py`, 726 qator — loyihadagi eng katta fayl) — vakansiyalar, reglament hujjatlari (DOCX/PDF/TXT, **versiyalash+rollback**), material AI-regeneratsiya (draft→tasdiq→faollashtirish), dars/test tahrirlash, to'liq audit log — HAMMASI kod o'zgartirmasdan

### ⚠️ Muhim topilma: qayta joylashtirish "tuzoq"i

`requirements.txt`da `openai>=1.30,<2` yozilgan va **`anthropic` umuman yo'q**, lekin jonli kod (`app/services/openai_service.py`) haqiqatda faqat `anthropic.AsyncAnthropic` chaqiradi — kodning hech bir joyida `openai` paketi ishlatilmaydi. `.env` ham faqat `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL` o'qiydi, `OPENAI_API_KEY` uchun sozlama umuman yo'q. Jonli venv'da ikkalasi ham qo'lda o'rnatilgan (`anthropic-0.109.2` va ishlatilmaydigan `openai-1.109.1`), lekin **agar kimdir `pip install -r requirements.txt` bilan noldan o'rnatsa, bot import xatosi bilan ishga tushmaydi** — bu OpenAI→Claude migratsiyasidan (06-16 sessiyasi) qolgan iz. README ham hali `OPENAI_API_KEY`/`OPENAI_MODEL=gpt-5.5` sozlashni aytadi — bu ham eskirgan.

**Kichik topilma:** `app/services/docx_reader.py` — hech qayerda chaqirilmaydigan o'lik kod (Dynamic Admin Panel qayta yozuvidan qolgan), xavfsiz o'chirsa bo'ladi.

### Texnologiyalar (haqiqatda kerak bo'lganlari)

`aiogram>=3.4,<4`, `anthropic` (requirements.txt'da yo'q — qo'lda qo'shish kerak!), `python-dotenv`, `python-docx`, `reportlab`, `openpyxl`, `apscheduler`, `pypdf`

### Konfiguratsiya

```env
BOT_TOKEN, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ADMIN_IDS, DB_PATH, EXPORT_DIR, LOG_FILE,
DEFAULT_SHOP_ADDRESS, DEFAULT_BRANCH, TIMEZONE, REGULATIONS_DIR, START_IMAGE_PATH,
CLOCKSTER_ENABLED, CLOCKSTER_API_BASE, CLOCKSTER_API_TOKEN, CLOCKSTER_EMPLOYEES_ENDPOINTS,
CLOCKSTER_ATTENDANCE_ENDPOINTS, CLOCKSTER_SYNC_INTERVAL_MINUTES, CLOCKSTER_LOOKBACK_DAYS, CLOCKSTER_MATCH_THRESHOLD
```
*(`CLOCKSTER_API_TOKEN` bot o'chiq bo'lsa ham boshqa joyda alohida ishlatiladi — [[clockster_api_write]] xotira yozuviga qarang.)*

### Fayllar

```
allmax_hr_bot/
├── main.py, TEST_REPORT.md
└── app/
    ├── bot.py, config.py, database.py (1363 qator, 27 jadval), states.py
    ├── handlers/  admin.py, dynamic_admin.py (726 qator), followup.py, interview.py,
    │              onboarding.py, resume.py, start.py, vacancies.py
    ├── services/  clockster_service, docx_reader (o'lik), dynamic_service, excel_service,
    │              lesson_service, material_service, openai_service (aslida Claude), pdf_service, scheduler_service
    ├── keyboards/, reglamentlar/ (12 hujjat + uploads/), exports/ (5 namuna PDF)
```

### Systemd

```
service: allmax-hr-bot
bot:     @allmax_jbot
holat:   disabled, inactive (2026-06-20dan)
```

---

# Joylashtirilmagan prototip

## 11. allmax_ai_assistant

> ⚠️ **Bu hech qachon systemd xizmati sifatida ishga tushirilmagan** — "to'xtatilgan xizmat" emas, balki bir marta yozilib tashlab qo'yilgan prototip kod.

### Nima uchun bu bo'lim boshqacha

`/etc/systemd/system/`da bu nom bilan hech qanday unit fayl yo'q va hech qachon bo'lmagan — butun fayl tizimi bo'ylab qidiruv, `journalctl`ning to'liq (vaqt bilan cheklanmagan) tarixi ham buni tasdiqladi: **nol yozuv**. Agar systemd biror marta bu xizmatni boshqargan bo'lsa, journald hech bo'lmasa "Started/Stopped" qatorini saqlab qolar edi — boshqa ikkita shunga o'xshash loyiha uchun bo'lgani kabi. To'liq yo'qlik — bu hech qachon ishga tushirilmagan degani.

### Nima uchun yaratilgan

Bitta commit (`b2ee176`, 2026-06-17, xabari: *"Telegram AI assistant for @allmax_claude_aiBot that controls allmax_telethon account... Uses modified Telethon with tmp_auth_key support"*) — `telegram_ai_assistant`ning aynan bir kunlik nusxasi (fork), lekin **ALLMAX biznes akkauntiga** (`telegram_ai_assistant`dagi kabi shaxsiy akkaunt o'rniga) yo'naltirilgan holda. Maqsad — xuddi shu "erkin tilda buyruq ber" patternini ALLMAXning asosiy Telegram akkaunti ustida ham qo'llash edi.

**Nega ehtimol ishga tushirilmagan (kuzatuvga asoslangan xulosa):** bir xil Telegram akkauntga ikkinchi parallel Telethon ulanish ochish MTProto sessiya to'qnashuvi/majburiy uzilishga olib kelishi mumkin — va aynan shu davrda jamoa `allmax_telethon`da shunga o'xshash bug bilan kurashayotgan edi (`receive_updates=False` tuzatishi ko'p o'tmay qo'shilgan). Jonli mijozlarga xizmat ko'rsatayotgan botni beqarorlashtirib qo'ymaslik uchun bu prototipni faqat sinab ko'rib, javonga qo'yib qo'yishgan degan xulosa eng izchil izoh.

**Dalil:** session fayli (`allmax_ai_session.session`) haqiqatda avtorizatsiyadan o'tgan (bir marta qo'lda login qilingan), lekin `conversation_history.json` atigi 1.1KB va commit vaqtidan beri o'zgarmagan — bir marta sinab ko'rilgan, keyin qaytib ishlatilmagan. Kod `telegram_ai_assistant`ning ancha soddaroq/erta versiyasi — foto/hujjat handler yo'q, video/HEIC tahlili yo'q, keyinroq qo'shilgan barqarorlik tuzatishlari yo'q.

### Xulosa

Bu "yoqish" kerak bo'lgan xizmat emas — agar kelajakda ALLMAX akkaunti uchun shunga o'xshash yordamchi kerak bo'lsa, bu kod boshlang'ich nuqta sifatida ishlatilishi mumkin, lekin avval `allmax_telethon` bilan bir vaqtda ishlash xavfsizligini (sessiya to'qnashuvi) hal qilish kerak bo'ladi.

### Systemd

```
Yo'q — hech qachon bo'lmagan.
```

---

# O'chirilgan loyihalar tarixi

Bu loyihalar serverda endi umuman yo'q (kod o'chirilgan). Faqat tarixiy kontekst uchun:

| Loyiha | O'chirilgan sana | Nima bo'lgan |
|---|---|---|
| `instagram_bitrix_dm_lead_bot` | 2026-06-26 | `allmax_instagram_agent` bilan **bir xil commit'da** almashtirildi (rename+rewrite). Faqat zararsiz, disabled, "orphan" systemd unit fayli qoladi (`instagram-dm-lead-bot.service`) — mavjud bo'lmagan papkaga ishora qiladi, ishga tushirilsa ham darhol xato beradi. |
| AllmaxHamkor (CTV platform) | 2026-08-08 (bugun, shu kundan oldinroq) | Foydalanuvchi so'rovi bilan to'liq o'chirildi. To'liq backup (kod+DB+config) serverda saqlanmoqda. |
| Allmax LinkBio | 2026-07-18 | Foydalanuvchi so'rovi bilan o'chirildi, backup saqlangan. |
| Asilbek Finance Bot | 2026-07-18 | Foydalanuvchining eski shaxsiy loyihasi, crash-loop holida topilib o'chirilgan. |
| `allmax_xm_trading_bot` | 2026-07-18 | Wine/MetaTrader orqali XM broker integratsiyasi urinishi, "kerak emas" deyilib to'liq tozalangan (Wine paketlari ham olib tashlangan, ~2GB bo'shatilgan). |

---

# ALLMAXga aloqasi yo'q — shaxsiy loyiha

## 12. narzullo_portfolio

> ⚠️ **Bu ALLMAX boti emas.** Server egasining shaxsiy portfolio sayti — faqat qulaylik uchun shu serverda joylashgan, ALLMAX biznes tizimlariga hech qanday aloqasi/kirishi yo'q.

### Nima bu

"Narzullo Muhammad Ali" — Cyber Security Engineer, OSCP sertifikatlangan (2026-yil 2-iyul) — uchun shaxsiy CV/portfolio sayti. Bo'limlar: bosh sahifa (terminal-uslub, animatsion tarmoq fon), professional xulosa, tajriba, sertifikatlar (OSCP, PDP grant, SAT, DTM — har biri to'liq rasm bilan), ko'nikmalar (Burp Suite, Nmap, Metasploit, Wireshark, BloodHound va h.k.), karyera vaqt chizig'i, ta'lim, aloqa (Telegram/Instagram/GitHub/email/xarita).

### Texnologiyalar

**Sof HTML/CSS/JS — freymvork yo'q, build jarayoni yo'q.** 4 ta manba fayl: `index.html`, `style.css` (1319 qator), `script.js` (404 qator), `i18n.js` (447 qator — EN/RU/UZ tarjima lug'ati va almashtiruvchi). Shriftlar Google Fonts CDN'dan. Faqat qorong'i rejim (light-theme yo'q).

### Qanday xizmat qilinadi

Nginx **to'g'ridan-to'g'ri statik fayl sifatida** (`root` + `try_files`), backend/baza yo'q. `/etc/nginx/sites-enabled/narzullayev.com` — HTTPS (Let's Encrypt, avto-yangilanadi) + HTTP→HTTPS redirect, `narzullayev.com` va `www.narzullayev.com` ikkalasi ham.

### Fayllar

```
narzullo_portfolio/
├── index.html, style.css, script.js, i18n.js
└── assets/  profile.jpg, oscp-preview.jpg, oscp-full.png, sat-score.jpg, dtm-admission.jpg, pdp-grant.jpg
```

### Eslatma

Ish daraxti (working tree) hozir commit qilingandan yangiroq (DTM/PDP-grant rasmlari qo'shilgan, IELTS bo'limi olib tashlangan, lekin hali commit qilinmagan) — statik sayt uchun shoshilinch emas, lekin qachondir commit qilib qo'yish tavsiya etiladi.

---

# Infratuzilma

## Server holati (2026-08-08 jonli tekshiruv)

| Servis | Holat | Port | Bot / Foydalanuvchi | RAM |
|---|---|---|---|---|
| `allmax-dashboard` | ✅ active, 0 restart | 8080 (ichki) | — | ~35 MB |
| `allmax-food-order-bot` | ✅ active, 0 restart | — | @food_control_rBot | ~144 MB |
| `bitrix-lead-alert-bot` | ✅ active, 0 restart | 8000 (tashqi yopiq) | — | ~87 MB |
| `feedback-bot` | ✅ active, 0 restart | — | @allmax_feedback_bot | ~114 MB |
| `food-control-bot` | ✅ active, 0 restart | — | @ovqatnazoratiuzbot | ~137 MB |
| `marketing-task-control-bot` | ✅ active, 0 restart | — | @allmax_vazifalarbot | ~92 MB |
| `allmax-telethon` | ⏸ disabled, inactive | — | @allmaxshaxsiy (biznes) | — |
| `telegram-ai-assistant` | ⏸ disabled, inactive | — | @Claude_ai_oBot | — |
| `allmax-instagram-agent` | ⏸ disabled, inactive | 8002 | — | — |
| `allmax-hr-bot` | ⏸ disabled, inactive | — | @allmax_jbot | — |
| `instagram-dm-lead-bot` | 🗑 orphan unit, papka yo'q | — | — | — |

Barchasi (`allmax-hr-bot`dan tashqari — u ham `enable`, lekin qo'lda `disable` qilingan) `systemctl enable`, `Restart=always` — server reboot bo'lsa faol xizmatlar avtomatik qayta ishga tushadi.

**6 faol xizmat 2026-07-31, 06:09 UTCdan beri barqaror ishlayapti** (`unattended-upgrades` avtomatik yangilanish tufayli birgalikda qayta ishga tushirilgan, halokat emas) — barchasi 0 restart.

## Nginx (allmax.tizm.uz va narzullayev.com)

| URL | Backend | Holat |
|---|---|---|
| `allmax.tizm.uz/dashboard/` | `127.0.0.1:8080` | ✅ Jonli, `allmax_dashboard`ga proxy |
| `allmax.tizm.uz/instagram/` | — | `410 Gone` (statik, Meta hali so'rov yubormoqda ~40-50K/kun) |
| `allmax.tizm.uz/tirox/` | — | O'lik portga proxy, lekin kuniga ~2 ta so'rov, muhim emas |
| `narzullayev.com` | Statik fayllar | ✅ Jonli, `narzullo_portfolio` |
| — | port 8000 (bitrix_lead_alert_bot) | Marshrut yo'q, UFW ham yopgan — faqat localhost |

## Firewall (UFW)

Faol, default-deny incoming: faqat 22 (SSH), 80, 443 (nginx) ochiq. Boshqa barcha port (8000, 8080 kiritilgan) faqat localhost orqali ishlaydi.

## Git / GitHub

```bash
cd /opt/AllmaxProjects
git add <fayllar>
git commit -m "o'zgarish tavsifi"
git push origin master
```
Repo **public**: [github.com/alishex/projects](https://github.com/alishex/projects). Push 2026-08-08dan beri ishlayapti (fine-grained PAT, faqat shu repo uchun, Contents: Read&write). **Muhim: `.env.example` fayllariga hech qachon haqiqiy qiymat yozmang** — bu fayllar odatda git'ga tushadi va public repoga push bo'ladi (2026-08-08da ikkita loyihada aynan shu xato topilib tuzatildi, yuqoridagi xavfsizlik bo'limiga qarang).

## Loglarni ko'rish

```bash
journalctl -u <service-name> -f          # Real vaqtda
journalctl -u <service-name> -n 50       # Oxirgi 50 qator
grep Accepted /var/log/auth.log          # SSH login tarixi (last -a ISHONCHSIZ, ishlatmang)
```

## Barcha faol servislarni qayta ishga tushirish

```bash
systemctl restart allmax-dashboard allmax-food-order-bot bitrix-lead-alert-bot \
  feedback-bot food-control-bot marketing-task-control-bot
```

## Deploy qilish (yangi/yangilangan loyiha)

```bash
rsync -avz --exclude venv --exclude __pycache__ --exclude .env --exclude "*.session" \
  ./loyiha/ root@209.38.239.245:/opt/AllmaxProjects/loyiha/
ssh allmaxhamkor-do "cd /opt/AllmaxProjects/loyiha && venv/bin/pip install -r requirements.txt && systemctl restart <service>"
```

## Utility skriptlar

| Fayl | Tavsif |
|---|---|
| `delete_tirox_leads.py` | Bitrix24'da TIROX integratsiyasi orqali tushgan leadlarni topib o'chiradi |
| `deploy.sh` | Umumiy deploy skripti |

---

*ALLMAX — Avtomatlashtirish va raqamli transformatsiya. Bu hujjat 2026-08-08da jonli server holati asosida to'liq qayta yozildi (5 ta parallel chuqur tekshiruv orqali) — oldingi versiya iyun oyidan beri yangilanmagan va bir qator joyda (Instagram loyiha almashinuvi, allmax_ai_assistant holati, food_control_bot/feedback_bot oqimlari, bitrix_lead_alert_bot endpoint'lari) noto'g'ri edi.*
