# ALLMAX Projects

**ALLMAX** (erkaklar kiyim-kechak chakana savdo brendi, Fix Price uslubida) kompaniyasining barcha avtomatlashtirish loyihalari — Telegram botlar, Instagram integratsiya, CRM alertlar, AI yordamchilar, HR tizimi va ichki dashboard. **Shu bilan birga, server egasining bir nechta shaxsiy (ALLMAXga aloqasi yo'q) loyihasi ham shu serverda joylashgan** — portfolio sayt, fitness app backend, shaxsiy moliya trekeri, ikkita onlayn-do'kon sahifasi. Pastda ikkalasi ham alohida bo'lim sifatida hujjatlangan.

**Server:** DigitalOcean VPS "tools" — Ubuntu 24.04 — `209.38.239.245` — 4 vCPU / 8 GB RAM (`s-4vcpu-8gb`) — disk 33% (16G/48G) — uptime 85+ kun (so'nggi reboot 2026-07-20/21 resize'dan beri yo'q)
**AI:** Anthropic Claude — umumiy/sherik kalit asosiy modeli loyihaga qarab `claude-opus-4-8` / `claude-sonnet-5` / `claude-haiku-4-5`. **⚠️ 2026-10-13'da yana "credit balance too low" bilan tugagan holatda — pastdagi operatsion ogohlantirishga qarang.** `moliya_bot` bu hisobdan mustaqil, alohida kalit ishlatadi.
**GitHub:** [alishex/projects](https://github.com/alishex/projects) (**public repo**) — 0 ahead / 0 behind. **2026-10-15'dan beri barcha 19 loyiha git-backed** (avval 5 tasi — jumladan shaxsiy moliya va mijoz ma'lumoti saqlovchi loyihalar — umuman kuzatilmagan edi).
**Bu hujjat oxirgi to'liq qayta yozilgan sana:** 2026-10-14 — 55 kunlik tanaffusdan keyingi "noldan tubdan" tekshiruv asosida (oldingi to'liq qayta yozish: 2026-08-08). 5 ta yangi loyiha (2026-10) qo'shildi, infratuzilma/xavfsizlik/billing bo'limlari jonli holatga mослаб yangilandi.
**2026-10-15 qo'shimcha (to'liq qayta yozish emas, faqat qo'shish):** 2 ta yangi ALLMAX biznes loyihasi — `allmax-fixprice` (to'liq onlayn-do'kon, bo'lim 18) va `allmax_taplink` (link-in-bio sahifa, `allmax.fixprice.org`, bo'lim 19) — hujjatlandi; Server holati / Nginx / SSL jadvallari mos ravishda yangilandi, qolgan 17 bo'lim tegilmadi.

---

## ⚠️ Xavfsizlik ogohlantirishlari

2026-08-08'dagi chuqur tekshiruvda topilgan 3 muammo — ikkitasi kod darajasida tuzatildi, lekin **haqiqiy kalitlarni almashtirish hali ham amalga oshirilmagan** (2026-10-14'da qayta tekshirildi — holat o'zgarmagan, pastdagi yangi topilmaga qarang):

1. **`allmax_dashboard/main.py`da login/parol ochiq matnda yozilgan edi** (git orqali kuzatiladigan faylda). ✅ Tuzatildi — endi `.env` fayliga ko'chirildi (git'ga kirmaydi), parolning o'zi o'zgarmadi. ⚠️ Eski qiymat hali git tarixida qoladi (`git log -p` orqali ko'rinadi) — **agar to'liq xavfsiz bo'lishni istasangiz, parolni almashtirish tavsiya etiladi**.
2. **`bitrix_lead_alert_bot/.env.example` va `marketing_task_control_bot/.env.example` fayllarida HAQIQIY Telegram bot tokenlari va Bitrix24 webhook manzili yozilgan edi** — public GitHub repoga push qilingan holda. ✅ Fayllar placeholder qiymatlarga almashtirildi. ⚠️ **Tavsiya hamon kuchda: ikkala botning Telegram tokenini @BotFather orqali va Bitrix24 webhookni qayta yarating** — eski qiymatlar hali git tarixida ochiq turibdi.
   **🆕 2026-10-14 topilma:** `allmax_instagram_agent/.env`dagi ikkita Meta/Instagram access tokeni (shu loyihada hech qachon git'ga tushmagan, repo untracked edi) Graph API orqali tekshirilganda "Session has expired on 2026-06-23" bilan **o'lik ekani tasdiqlandi** — bu tokenlar endi baribir ishlamaydi, amaliy xavf kamaydi, lekin bu bitta aniq misol sifatida ko'rsatadiki, serverda eskirgan/o'lik tokenlar ko'p — qolgan (Bitrix/Telegram) qiymatlarning hali ham amal qilib-qilmasligi alohida tekshirilmagan.
3. **`bitrix_lead_alert_bot`ning "real-time webhook"i aslida tashqaridan yetib bo'lmaydi** (8000-port UFW'da yopiq) — amalda faqat **60 soniyalik backup polling** orqali ishlaydi. Ishonchli (minglab lead muvaffaqiyatli yetkazilgan), shunchaki "real-time" degani unchalik to'g'ri emas.

Bulardan tashqari, `allmax_dashboard`dagi "Tizim holati" paneli **jonli emas — qattiq yozilgan (hardcoded)**, faqat stat-kartalar/grafik/kontaktlar ro'yxati haqiqiy.

---

## ⚠️ Operatsion ogohlantirish — umumiy Anthropic balansi

Deyarli barcha ALLMAX botlari **va endi 2 ta shaxsiy loyiha ham** (`ozish_backend`, `shifokor_yordamchisi`) bitta umumiy Anthropic Console hisobidan (`ANTHROPIC_API_KEY`) foydalanadi. Bu hisob kredit tugashi bilan hozirgacha **3 marta** to'xtagan: 2026-07-05, 2026-08-30, va 2026-10-11 (so'nggisi **2026-10-13'da qayta tekshirilganda ham hali tugagan holatda tasdiqlandi** — hozirgacha eng uzoq davom etayotgan holat). Faqat console.anthropic.com orqali, faqat server egasi to'ldira oladi — Claude'ning billing'ga kirish huquqi yo'q. Bu endi faqat ichki botlarni emas, balki sotilishi rejalashtirilgan mahsulotning (`shifokor_yordamchisi`) mijozga ko'rinadigan AI-funksiyasini ham buzmoqda.

**`moliya_bot` bu muammodan butunlay mustaqil** — alohida/ajratilgan Anthropic kaliti ishlatadi, shared billing tugashi unga ta'sir qilmaydi.

**Qoida:** istalgan botning Claude-funksiyasi xato bersa yoki jim qolsa, kod xatosini qidirishdan OLDIN billing holatini tekshiring — bu hozirgacha haqiqiy sabab 3 marta bo'lgan.

---

## Loyihalar ro'yxati

### ALLMAX biznes loyihalari

| # | Loyiha | Holat | Tavsif | Port | RAM (10-14) |
|---|---|---|---|---|---|
| 1 | [allmax_dashboard](#1-allmax_dashboard) | ✅ Faol | Telethon agent statistikasi uchun ichki web dashboard | 8080 (ichki) | 34 MB |
| 2 | [allmax_food_order_bot](#2-allmax_food_order_bot) | ✅ Faol | 7 bo'lim uchun kunlik ovqat buyurtma + Owner Panel | — | 145 MB |
| 3 | [bitrix_lead_alert_bot](#3-bitrix_lead_alert_bot) | ✅ Faol | Bitrix24 yangi lead → Telegram guruh alert (amalda polling) | 8000 (tashqi yopiq) | 72 MB |
| 4 | [feedback_bot](#4-feedback_bot) | ✅ Faol | Mijoz fikr-mulohaza (reyting, media, telefon) yig'ish | — | 119 MB |
| 5 | [food_control_bot](#5-food_control_bot) | ✅ Faol | Marketing bo'limi ovqat nazorati (12 xodim faol) | — | 137 MB |
| 6 | [marketing_task_control_bot](#6-marketing_task_control_bot) | ✅ Faol | Vazifalar + Eisenhower matritsa grafik hisobot | — | 94 MB |
| 7 | [allmax_telethon](#7-allmax_telethon) | ⏸ To'xtatilgan (07-24) | ALLMAX biznes akkaunt — Community Agent (savdo/support) | — | — |
| 8 | [telegram_ai_assistant](#8-telegram_ai_assistant) | ⏸ To'xtatilgan (07-08) | Egasining shaxsiy akkaunti uchun Claude yordamchi | — | — |
| 9 | [allmax_instagram_agent](#9-allmax_instagram_agent) | ⏸ To'xtatilgan (06-28) | Instagram DM Community Agent (telethon'ning egizagi) | 8002 (410 qaytadi) | — |
| 10 | [allmax_hr_bot](#10-allmax_hr_bot) | ⏸ To'xtatilgan (06-20) | To'liq HR pipeline: ariza → AI intervyu → onboarding | — | — |
| 11 | [allmax_ai_assistant](#11-allmax_ai_assistant) | 🚫 Hech qachon ishga tushirilmagan | Tashlab qo'yilgan prototip (telegram_ai_assistant fork'i) | — | — |
| — | [instagram_bitrix_dm_lead_bot](#ochirilgan-loyihalar-tarixi) | 🗑 To'liq o'chirilgan (06-26) | Eski Instagram bot — allmax_instagram_agent bilan almashtirilgan | — | — |
| 18 | [allmax-fixprice](#18-allmax-fixprice) | ✅ Faol (10-15, yengil tekshirilgan) | To'liq onlayn-do'kon — katalog, buyurtma, admin | 8040 (ichki) | 37 MB |
| 19 | [allmax_taplink](#19-allmax_taplink) | ✅ Faol (static) | Allmax Fix Price link-in-bio sahifasi | allmax.fixprice.org | — (static) |

> **Jami RAM (7 faol ALLMAX bot/xizmat):** ~638 MB / 8 GB.

### Shaxsiy loyihalar (ALLMAXga aloqasi yo'q)

| # | Loyiha | Holat | Tavsif | Manzil | RAM (10-14) |
|---|---|---|---|---|---|
| 12 | [narzullo_portfolio](#12-narzullo_portfolio) | ✅ Faol (static) | Server egasining shaxsiy CV/portfolio sayti | narzullayev.com | — (static) |
| 13 | [ozish_backend](#13-ozish_backend) | ✅ Faol | Fitness/ozish mobil ilovasi backend (FastAPI) | narzullayev.com/ozish-api/ | 91 MB |
| 14 | [moliya_bot](#14-moliya_bot) | ✅ Faol | Shaxsiy kirim-chiqim (moliya) trekeri Telegram bot | @meningbugalterimbot | 692 MB |
| 15 | [intim-shop-parfume](#15-intim-shop-parfume) | ✅ Faol | INTIM SHOP — onlayn do'kon + Telegram admin | intimshop.net | 49 MB |
| 16 | [shifokor_yordamchisi](#16-shifokor_yordamchisi) | ✅ Faol | Ekhokardiografiya ta'lim/klinik platforma | shifokor.narzullayev.com | 16 MB |
| 17 | [moxa_taplink](#17-moxa_taplink) | ✅ Faol (static) | "Moxa Parfume" link-in-bio sahifasi | moxa.intimshop.net | — (static) |

> **Jami RAM (barcha 11 faol xizmat, ALLMAX+shaxsiy):** ~1.49 GB / 8 GB. Server umumiy: 2.0Gi/7.8Gi ishlatilmoqda (boshqa xizmatlar — nginx/postgres/redis/OS — bilan birga), disk 33% (16G/48G), uptime 86+ kun.

---

# Faol loyihalar — ALLMAX

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

Frontend — vanilla JS + Tailwind (CDN) + Chart.js (CDN), build qadam yo'q. Har 30 soniyada avto-yangilanadi. `docs_url=None` — Swagger/ReDoc atayin o'chirilgan.

**Muhim:** "Tizim holati" paneli (allmax-telethon/Anthropic/MoySklad/Bitrix24 belgilari) **statik/qattiq yozilgan — hech qanday backendga ulanmagan**. Faqat 4 ta stat-karta, grafik va kontaktlar ro'yxati jonli.

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `fastapi` | Web server |
| `uvicorn[standard]` | ASGI server |
| `python-multipart` | Login form parsing |
| `aiofiles` | Statik fayllarga async kirish |
| `python-dotenv` | `.env`dan login/parol o'qish |

### Konfiguratsiya

```env
DASHBOARD_EMAIL, DASHBOARD_PASSWORD
```

### Fayllar

```
allmax_dashboard/
├── main.py            — Butun FastAPI ilova (auth + API), ~160 qator
├── requirements.txt
├── .env               — (gitignored)
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
1. Har kuni belgilangan vaqtda (standart **17:00**, DB orqali o'zgartiriladi) scheduler har bo'lim adminiga ertangi menyuni (**3 haftalik** aylanma sikl) va "📝 Buyurtma berish" tugmasini yuboradi
2. Admin tushlik va kechki ovqat porsiya sonini kiritadi → tasdiqlaydi → `department_orders` jadvaliga yoziladi
3. `/edit` — tasdiqlangan buyurtmani qayta tahrirlash
4. **O'rinbosarga yuborish** — admin kunlik so'rovni o'rinbosarga bir martalik topshirishi mumkin
5. **"Boshliqlar" bo'limi "fixed"** — DBda qayd etilgan doimiy son (3/2), admin kerak emas, scheduler avtomatik yozadi
6. Doimiy tugmalar: **"🍽 Yakuniy hisobot"** (video-note bilan qoldiq ovqat isboti), **"💬 Fikr-mulohaza"**
7. Bir foydalanuvchi uchun parallel buyurtma/hisobot/feedback boshlanishini bloklaydigan "conflict guard"

**B) Owner Panel (`/owner`, faqat `OWNER_IDS`, 2 ta owner):**
- 📊 Ertangi holat, ✏️ Buyurtma kiritish (override), 🏢 Bo'limlar CRUD, 👑 Ownerlar, 📝 Menyu (21 kunlik sikl), 🔄 Sikl, 🕐 Vaqtlar, 📋 Hisobotni hozir olish

**Muhim dizayn qarori:** `.env`dagi qiymatlar faqat birinchi ishga tushirishda "seed" sifatida ishlatiladi — shundan keyin **baza yagona haqiqat manbai**.

**Menyu:** 2026-08-22'da 1- va 2-hafta "Xasanov" kontaktidan kelgan yangi Sharqona Catering menyusi bilan yangilandi (3-hafta ataylab tegilmadi, hali 08-08'dagi eski taomlar).

### Texnologiyalar

`aiogram==3.17.0`, `apscheduler==3.10.4`, `aiosqlite==0.20.0`, `pytz==2024.2`

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
├── main.py                — Bot ishga tushirish
├── data/orders.db          — Jonli SQLite (menu, settings, department_orders, departments, owners)
└── app/
    ├── config.py, database.py, keyboards.py, scheduler.py, states.py
    ├── handlers/admin.py, handlers/owner.py
    └── services/menu_service.py, report_service.py
```

### Systemd

```
service: allmax-food-order-bot
bot:     @food_control_rBot (id 8877062313)
port:    yo'q (long-polling)
```

---

## 3. bitrix_lead_alert_bot

> Bitrix24 CRMga yangi lead tushganda Telegram guruhiga xabar yuboradi. **Amalda faqat 60 soniyalik polling orqali ishlaydi.**

### Nima qiladi

1. **Backup polling** — har 60s Bitrix24 `crm.item.list` so'raladi
2. **Realtime-baseline himoyasi** — eski leadlar hech qachon xato alert qilinmaydi
3. **Kontakt boyitish**, **qayta urinish** (5 marta), Telegram tezlik cheklovi

**Endpoint'lar:**
```
GET  /health
POST /bitrix/lead
POST /manual/lead/{lead_id}
POST /admin/retry-pending
```

### Texnologiyalar

`fastapi`, `uvicorn[standard]`, `apscheduler`, `httpx`, `pydantic`

### Konfiguratsiya

```env
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_MENTION_USER_ID, TELEGRAM_MENTION_NAME,
BITRIX_WEBHOOK_BASE_URL, BITRIX_PORTAL_URL, WEBHOOK_SECRET,
APP_HOST, APP_PORT, TIMEZONE, LOG_LEVEL, DATABASE_PATH, LOG_FILE,
POLL_INTERVAL_SECONDS, POLL_LOOKBACK_LIMIT, RETRY_MAX_ATTEMPTS, RETRY_BASE_DELAY_SECONDS,
REQUEST_TIMEOUT_SECONDS, REALTIME_ONLY_MODE, POLL_SEND_UNKNOWN_ON_START, TELEGRAM_MIN_DELAY_SECONDS
```

### Fayllar

```
bitrix_lead_alert_bot/
├── run.py, Dockerfile, docker-compose.yml
├── data/bot.db, logs/bot.log
├── scripts/get_chat_id.py
└── app/ main.py, bitrix.py, telegram_client.py, processor.py, scheduler.py, database.py, config.py
```

### Systemd

```
service: bitrix-lead-alert-bot
port:    8000 (localhost, tashqaridan YOPIQ)
```

---

## 4. feedback_bot

> Mijozlardan 1–5 baho + matn/media/telefon yig'uvchi bot. Har mijoz uchun yig'ma (rolling) xulosa xabarini admin guruhida yangilab turadi.

### Nima qiladi

1. `/start` → "📝 Fikr qoldirish"
2. Foydalanuvchi avval kontent yuboradi (matn/rasm/video/ovoz)
3. 1–5 yulduz so'raladi
4. Telefon raqami so'raladi (ixtiyoriy)
5. Barcha ma'lumot `ADMIN_CHAT_ID`ga yuboriladi
6. Har foydalanuvchi tarixi saqlanadi — yangi fikr kelganda admin guruhidagi eski xabar o'chirilib, yangilangan yig'ma karta qayta yuboriladi
7. Saqlash atomik (`feedbacks.json.tmp` → `os.replace()`)

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

1. **Menyu yuborish** (13:30 Toshkent) — 21 kunlik (3 haftalik) sikldan ertangi menyu, inline tugmalar bilan
2. Foydalanuvchi javob beradi → barcha faol foydalanuvchilar javob bersa, admin avtomatik hisobot oladi
3. **Ovqat eyilgani isboti** — video-note orqali
4. **Yakuniy hisobot** (22:00) — kunlik hisob-kitob

**Admin:** eski matn buyruqlari + yangi `/admin` inline panel (xodimlarni qo'shish/o'chirish, buyurtma o'zgartirish, menyu/sikl/vaqt sozlash, ko'p-adminlilik).

**Faol xodimlar: 12** (13tadan 2tasi admin panel orqali soft-remove qilingan). **Menyu 2026-08-22'da 1- va 2-hafta uchun "Xasanov" kontaktidan yangilandi** (3-hafta eski, 08-08'dagi Sharqona taomlari).

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
    ├── handlers/  admin.py, callbacks.py, user.py
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

1. Admin xodimga vazifa yaratadi (P1–P4 muhimlik)
2. Xodim deadline taklif qiladi → admin tasdiqlaydi → `ACTIVE`
3. Eslatmalar — 24s/3s/1s qolganda, muddati o'tsa avtomatik `OVERDUE`
4. Xodim yakunlaydi → admin xabar oladi
5. **Grafik hisobot** (Pillow) — shablon asosida, har vazifa auto word-wrap bilan

### Texnologiyalar

`aiogram>=3.7,<4`, `aiosqlite`, `apscheduler>=3.10,<4`, `Pillow`, `pytest`

### Konfiguratsiya

```env
BOT_TOKEN, ADMIN_ID, TIMEZONE, DATABASE_PATH, LOG_LEVEL
```

### Fayllar

```
marketing_task_control_bot/
├── bot.py, config.py
├── database/  database.py, models.py, repositories.py
├── handlers/  admin, common, employee, graph_reports, settings, task_creation, task_management
├── services/  cleanup_service, matrix_image_service, notification_service, priority_service, reminder_service, task_service
├── middlewares/ auth_middleware.py
├── assets/    toliq_ish_vazifalar_template.png
└── tests/
```

### Systemd

```
service: marketing-task-control-bot
bot:     @allmax_vazifalarbot (id 8061098327)
```

---

# To'xtatilgan loyihalar — ALLMAX

*Kod serverda bor, systemd xizmat ham mavjud, lekin hozir `disabled`+`inactive`. 2026-10-14'da qayta tekshirildi — barchasi hali ham o'zgarishsiz to'xtagan holatda.*

## 7. allmax_telethon

> ALLMAX biznes Telegram akkaunti nomidan ishlaydigan **Community Agent** — mijozlar bilan avtomatik suhbat, MoySklad stok tekshiruvi, Bitrix24 CRM/Projects integratsiyasi. Eng ko'p ishlab chiqilgan loyiha.

### To'xtatilgan sana va sababi

**2026-07-24, 09:16** — atayin, toza to'xtatish.

### Nima qiladi

- Telethon orqali kelgan DM'larni (matn/ovoz/video/rasm/GIF/stiker) qabul qiladi, 1.8s burst-collector bilan birlashtiradi
- Claude oxirgi 30 kunlik tarixni ko'rib javob beradi (UZ/RU/EN avtomatik)
- **Operator ustuvorligi** — inson operator yozsa, agent jim bo'lib qoladi
- `check_stock` (MoySklad, 600s cache), `order_complete` (Bitrix24), `needs_human`, `share_location`
- Har kuni 00:00 UZTda kunlik hisobot

### Texnologiyalar

`telethon`, `anthropic`, `faster-whisper`, `ffmpeg`, `sqlite3`, `requests` — ⚠️ `requirements.txt` bu loyihada YO'Q.

### Konfiguratsiya (asosiylari)

```env
TELEGRAM_API_ID, TELEGRAM_API_HASH, PHONE_NUMBER, SESSION_NAME, ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
COMMUNITY_AGENT_ENABLE, COMMUNITY_HISTORY_LIMIT, COMMUNITY_HISTORY_DAYS, COMMUNITY_ADDRESS,
COMMUNITY_WORK_START, COMMUNITY_WORK_END, LEAD_GROUP, MESSAGE_BURST_WINDOW, MAX_BURST_MESSAGES,
MOYSKLAD_TOKEN, BITRIX_ENABLE, BITRIX_WEBHOOK_URL, BITRIX_PROJECT_* (7 ta qo'shimcha)
```

### Fayllar

```
allmax_telethon/
├── main_ready_project.pyw   — Asosiy
├── community_agent.py        — Claude agent
├── media_handler.py          — Whisper + vizual
├── moysklad.py                — Stok tekshiruv
├── allmax_cm_session.session
└── analytics/                 — SQLite bazalar
```

### Systemd

```
service: allmax-telethon
holat:   disabled, inactive (2026-07-24dan)
```

---

## 8. telegram_ai_assistant

> Egasining **shaxsiy** Telegram akkaunti uchun umumiy maqsadli Claude yordamchisi.

### To'xtatilgan sana va sababi

**2026-07-08, 21:36** — oldin halokatli tsikl (9462+ restart) bo'lgan, session avtorizatsiyasi tugab qolgan. Qayta tiklangan ko'rinadi, lekin shundan beri qayta ishga tushirilmagan.

### Nima qiladi

- `@Claude_ai_oBot` orqali OWNER_USER_ID'dan kelgan xabarni "topshiriq" deb qabul qiladi
- Claude agentik tool-use loop (maks 25 qadam): `list_dialogs`, `get_chat_history`, `search_messages`, `send_message`, `get_chat_info`, `get_current_datetime`
- Eng boy media pipeline: ovoz/video/audio, rasm, HEIC/HEIF
- `file_reader.py` — PDF/Word/Excel/CSV

### Texnologiyalar

```
telethon==1.36.0, anthropic>=0.40.0, aiogram==3.15.0, python-dotenv==1.1.1, faster-whisper>=1.0.0
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
├── bot.py, claude_agent.py, telegram_client.py
├── media_transcriber.py, file_reader.py
├── memory_store.py, config.py, login_session.py
```

### Systemd

```
service: telegram-ai-assistant
bot:     @Claude_ai_oBot
holat:   disabled, inactive (2026-07-08dan)
```

---

## 9. allmax_instagram_agent

> `allmax_telethon`ning Instagram egizagi — Claude AI Community Agent, Meta Webhook orqali Instagram DM'larga javob beradi.

### To'xtatilgan sana va sababi

**~2026-06-27/28** — Instagram Graph API `400 Bad Request` (token eskirgan) + Anthropic kredit tugashi.

### Nima qiladi

- FastAPI + Meta Webhook (HMAC-SHA256 imzo tekshiruv)
- Har DM: dublikat tekshiruv → Claude javob → Instagramga yuborish → telefon/ism ajratish → Bitrix24 Lead+Project → Telegram bildirishnoma
- Target/reklama aniqlash

### Nginx marshruti

```nginx
location /instagram/ {
    return 410;  # backend 06-28dan o'chirilgan
}
```

**🆕 2026-10-14 — Meta webhook to'foni amalda tugaganga o'xshaydi.** Iyul-avgustda kuniga 40-50K so'rov (barchasi 410 javob) kelib turgan edi — 2026-10-14'dagi 7.6 soatlik namunada atigi 31 ta so'rov chiqdi (~99.8% pasayish, taxminan ~100/kun). To'liq 24 soatlik namuna bilan hali rasman tasdiqlanmagan, lekin kuchli signal.

**🆕 2026-10-14 — ikkala Meta access token (`META_IG_USER_ACCESS_TOKEN`, `META_PAGE_ACCESS_TOKEN`) Graph API orqali tekshirilganda o'lik (muddati 2026-06-23'da tugagan) ekani tasdiqlandi.** Qayta yoqishdan oldin bari bir yangi token olish shart bo'lar edi.

### Texnologiyalar

```
fastapi==0.115.8, uvicorn[standard]==0.34.0, httpx==0.28.1, pydantic==2.10.6, anthropic>=0.40.0
```

### Konfiguratsiya (qisqartirilgan — ~45 o'zgaruvchi)

```env
META_API_MODE, META_VERIFY_TOKEN, META_APP_SECRET, META_IG_USER_ACCESS_TOKEN, META_PAGE_ACCESS_TOKEN,
META_IG_BUSINESS_ID, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, BITRIX_* (14 ta), LEAD_TELEGRAM_* (9 ta),
TARGET_VIDEO_*, COMMUNITY_AGENT_ENABLE, COMMUNITY_WORK_START/END, MOYSKLAD_TOKEN
```

### Fayllar

```
allmax_instagram_agent/
├── run.py, Dockerfile, docker-compose.yml
└── app/
    ├── main.py, config.py, database.py, models.py, logger.py
    ├── routes/webhook.py
    ├── services/ community_agent.py, moysklad.py, bitrix_service.py, instagram_service.py,
    │             telegram_service.py, duplicate_service.py, target_detector.py, meta_signature.py
    └── workers/conversation_sync.py
```

### Systemd

```
service: allmax-instagram-agent
holat:   disabled, inactive (~2026-06-27/28dan)
```

⚠️ **Qayta yoqishdan oldin:** yangi Instagram access token (eskisi o'lik, tasdiqlangan) va Anthropic kredit balansini (hali tugagan) tekshiring.

---

## 10. allmax_hr_bot

> ALLMAX uchun to'liq HR avtomatlashtirish — vakansiya arizasidan yakuniy testgacha, 27 jadvalli baza bilan.

### To'xtatilgan sana

**2026-06-20, 13:03** — qo'lda SIGTERM.

### Nima qiladi

1. **Ariza** — 23 savolli anketa → tajriba → rasm → rozilik → draft-resume
2. **AI intervyu** — javoblar 0–100 ball, admin tavsiyasi, AI ishlamasa heuristik zaxira
3. **PDF eksport**, **Follow-up**, **7 kunlik onboarding** (20 dars + testlar)
4. **Clockster integratsiyasi** — stajirovka tugagandan keyin
5. **Dinamik admin panel** — kod o'zgartirmasdan vakansiya/reglament/dars boshqaruvi

### ⚠️ Muhim topilma: qayta joylashtirish "tuzoq"i

`requirements.txt`da `openai` bor, `anthropic` YO'Q — lekin kod faqat Anthropic chaqiradi. Noldan o'rnatilsa import xatosi bilan ishga tushmaydi.

### Texnologiyalar (haqiqatda kerak bo'lganlari)

`aiogram>=3.4,<4`, `anthropic` (requirements.txt'da yo'q!), `python-dotenv`, `python-docx`, `reportlab`, `openpyxl`, `apscheduler`, `pypdf`

### Konfiguratsiya

```env
BOT_TOKEN, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ADMIN_IDS, DB_PATH, EXPORT_DIR, LOG_FILE,
DEFAULT_SHOP_ADDRESS, DEFAULT_BRANCH, TIMEZONE, REGULATIONS_DIR, START_IMAGE_PATH,
CLOCKSTER_ENABLED, CLOCKSTER_API_BASE, CLOCKSTER_API_TOKEN, CLOCKSTER_EMPLOYEES_ENDPOINTS,
CLOCKSTER_ATTENDANCE_ENDPOINTS, CLOCKSTER_SYNC_INTERVAL_MINUTES, CLOCKSTER_LOOKBACK_DAYS, CLOCKSTER_MATCH_THRESHOLD
```

### Fayllar

```
allmax_hr_bot/
├── main.py, TEST_REPORT.md
└── app/
    ├── bot.py, config.py, database.py (1363 qator, 27 jadval), states.py
    ├── handlers/  admin.py, dynamic_admin.py (726 qator), followup.py, interview.py,
    │              onboarding.py, resume.py, start.py, vacancies.py
    ├── services/  clockster_service, dynamic_service, excel_service, lesson_service,
    │              material_service, openai_service (aslida Claude), pdf_service, scheduler_service
    ├── keyboards/, reglamentlar/, exports/
```

### Systemd

```
service: allmax-hr-bot
bot:     @allmax_jbot
holat:   disabled, inactive (2026-06-20dan)
```

---

# Joylashtirilmagan prototip — ALLMAX

## 11. allmax_ai_assistant

> ⚠️ **Bu hech qachon systemd xizmati sifatida ishga tushirilmagan** — bir marta yozilib tashlab qo'yilgan prototip kod.

Bitta commit (`b2ee176`, 2026-06-17) — `telegram_ai_assistant`ning ALLMAX biznes akkauntiga yo'naltirilgan fork'i. Ehtimol bir xil akkauntga ikkinchi parallel Telethon ulanish sessiya to'qnashuviga olib kelishi xavfi tufayli javonga qo'yib qo'yilgan. Kelajakda kerak bo'lsa boshlang'ich nuqta sifatida ishlatilishi mumkin.

```
Systemd: yo'q — hech qachon bo'lmagan.
```

---

# O'chirilgan loyihalar tarixi

Bu loyihalar serverda endi umuman yo'q (kod o'chirilgan). Faqat tarixiy kontekst uchun:

| Loyiha | O'chirilgan sana | Nima bo'lgan |
|---|---|---|
| `instagram_bitrix_dm_lead_bot` | 2026-06-26 | `allmax_instagram_agent` bilan bir xil commit'da almashtirildi |
| AllmaxHamkor (CTV platform) | 2026-08-08 | Foydalanuvchi so'rovi bilan to'liq o'chirildi, backup saqlanmoqda |
| Allmax LinkBio | 2026-07-18 | Foydalanuvchi so'rovi bilan o'chirildi, backup saqlangan |
| Asilbek Finance Bot | 2026-07-18 | Eski shaxsiy loyiha, crash-loop holida topilib o'chirilgan |
| `allmax_xm_trading_bot` | 2026-07-18 | Wine/MetaTrader XM broker urinishi, "kerak emas" deyilib tozalangan |

---

# Shaxsiy loyihalar (ALLMAXga aloqasi yo'q)

*Server egasining shaxsiy/mustaqil loyihalari — faqat qulaylik uchun shu serverda joylashgan, ALLMAX biznes tizimlariga hech qanday aloqasi/kirishi yo'q. Hammasi 2026-10-14'dan boshlab git-backed.*

## 12. narzullo_portfolio

> Server egasining shaxsiy portfolio sayti — "Narzullo Muhammad Ali", Cyber Security Engineer, OSCP sertifikatlangan.

### Nima bu

CV/portfolio sayti: bosh sahifa (terminal-uslub, animatsion tarmoq fon), professional xulosa, tajriba, sertifikatlar (OSCP, PDP grant, SAT, DTM), ko'nikmalar, karyera vaqt chizig'i, ta'lim, aloqa. To'liq uch tilli (EN/RU/UZ), faqat qorong'i rejim.

### Texnologiyalar

Sof HTML/CSS/JS — freymvork yo'q, build jarayoni yo'q. `index.html`, `style.css`, `script.js`, `i18n.js`.

### Qanday xizmat qilinadi

Nginx to'g'ridan-to'g'ri statik fayl sifatida. `/etc/nginx/sites-enabled/narzullayev.com` — HTTPS (Let's Encrypt, muddati 2026-12-16, avto-yangilanadi) + HTTP→HTTPS redirect.

### Fayllar

```
narzullo_portfolio/
├── index.html, style.css, script.js, i18n.js
└── assets/  profile.jpg, oscp-*.jpg/png, sat-score.jpg, dtm-admission.jpg, pdp-grant.jpg
```

### Eslatma

Doimiy ravishda ish jarayonida (hozir ham SEO/sitemap bo'yicha uncommitted o'zgarish bor) — statik sayt uchun shoshilinch emas.

---

## 13. ozish_backend

> "Ozish" — shaxsiy ozish/fitness native mobil ilovasi (Expo/React Native, mobil qism serverda emas, mahalliy `~/ozish-app/`da) uchun backend. 2026-08-30'da qurilgan.

### Nima qiladi

- **Autentifikatsiya** — JWT (email+parol, bcrypt)
- **Ovqat kundaligi** — Claude Haiku orqali ovqat tavsifidan avtomatik kaloriya/BJU ajratish (tool-use)
- **Vazn/progress grafik**, **mashq jurnali**, **kunlik eslatmalar** — APScheduler har daqiqa `reminders.time_of_day`ni tekshirib, Expo push (`https://exp.host/--/api/v2/push/send`) yuboradi
- **AI murabbiy chat** — Claude Sonnet 5 orqali suhbat
- Ikkala Claude chaqiruvi ham **graceful degradation** bilan o'ralgan — billing tugasa ovqat kundaligi AI'siz ham saqlanadi, murabbiy toza 503 qaytaradi (2026-08-30'da birinchi kunning o'zida kerak bo'lgan)

### Texnologiyalar

```
fastapi==0.115.6, uvicorn[standard]==0.32.1, sqlalchemy==2.0.36, psycopg2-binary==2.9.10,
passlib[bcrypt]==1.7.4, python-jose[cryptography]==3.3.0, pydantic[email]==2.10.3,
anthropic==0.109.2, httpx==0.28.1, apscheduler==3.10.4
```

### Konfiguratsiya

```env
DATABASE_URL, JWT_SECRET, JWT_EXPIRE_MINUTES, ANTHROPIC_API_KEY, CLAUDE_FAST_MODEL, CLAUDE_COACH_MODEL
```

### Fayllar

```
ozish_backend/
├── requirements.txt
└── app/
    ├── __init__.py, auth.py, config.py, database.py, main.py, models.py, schemas.py
    ├── routers/  auth.py, coach.py, food.py, push.py, reminders.py, weight.py, workouts.py
    └── services/ claude_client.py, push_service.py, scheduler.py
```

### Ma'lumotlar bazasi

Umumiy serverdagi Postgres instansiyasida alohida/izolyatsiyalangan: baza `ozish_app`, rol `ozish_user`.

### Systemd va tarmoq

```
service: ozish-backend
port:    127.0.0.1:8010 (uvicorn)
nginx:   https://narzullayev.com/ozish-api/  →  mavjud narzullayev.com vhost'iga qo'shilgan location bloki
```

---

## 14. moliya_bot

> Shaxsiy (ALLMAXga aloqasi yo'q) kirim-chiqim trekeri Telegram bot — `@meningbugalterimbot`. 2026-10-11'da ishga tushirilgan.

### Nima qiladi

- Xarajat/daromad/qarz kuzatuvi — summalar **INTEGER tiyin**da saqlanadi (float emas, tin-tinigacha aniqlik)
- UZS + USD, tabiiy format tushunadi ("50000"/"1.5 mln"/"50 ming"/"$100")
- Naqd/karta alohida + umumiy jami
- Kunlik/haftalik/oylik dashboard, kategoriya limiti (🟢🟡🔴), oylik limit ogohlantirishi
- Qarz (berish/olish/yopish) moduli
- **Ovozli+erkin matnli kiritish** — faster-whisper (lokal, "small" model) transkripsiya → Claude Haiku strukturaga o'giradi → har doim ✅/❌ tasdiqlash bilan
- CSV hisobot eksport (utf-8-sig, Excel'da kirill to'g'ri ochiladi)

**⚠️ RAM: ~692 MB — serverdagi eng og'ir shaxsiy loyiha** (faster-whisper + onnxruntime kutubxonalari jarayon ichida yuklanadi).

**Muhim:** `OWNER_ID` (`5033652594`) — bu ALLMAX/narzullo_portfolio egasining asosiy Telegram akkaunti (`8889307131`, @the_narzullayev) **EMAS**, alohida/boshqa akkaunt.

### Texnologiyalar

```
aiogram==3.13.1, aiosqlite==0.20.0, pytz==2024.1, anthropic>=0.40.0, faster-whisper>=1.0.3
```

### Konfiguratsiya

```env
BOT_TOKEN, OWNER_ID, ANTHROPIC_API_KEY (mustaqil/alohida kalit), NLU_MODEL, DB_PATH, TIMEZONE, WHISPER_MODEL_SIZE
```

### Fayllar

```
moliya_bot/
├── main.py, requirements.txt, moliya.db
└── app/
    ├── __init__.py, categories.py, config.py, database.py, keyboards.py, utils.py
    ├── handlers/  expense, income, debt, dashboard, list_tx, report, settings, freeform, start
    └── services/  debt_service, fx_service, nlu_service, tx_service, voice_service
```

### Systemd

```
service: moliya-bot
bot:     @meningbugalterimbot (id 8972499267)
port:    yo'q (long-polling)
```

---

## 15. intim-shop-parfume

> **INTIM SHOP** — kattalar/intim mahsulotlari (vibratorlar, o'yinchoqlar, lubrikant) uchun to'liq onlayn-do'kon + Telegram admin. 2026-10-09'da qurilgan.

### Nima qiladi

- 20 kategoriyali katalog, razmer/rang variant modeli
- **Server-tomonli narxlash**, idempotent buyurtmalar, tranzaksion stok, sanab bo'lmaydigan (non-enumerable) kuzatuv tokenlari
- **To'lov:** faqat yetkazib berilganda naqd — saytda hech qanday to'lov matni yo'q (ataylab, call-center orqali tushuntiriladi)
- Geolokatsiya (brauzer native API) → Telegram'ga real xarita sifatida yuboriladi
- **Ikkita admin interfeys, bir-biriga sinxron:** veb (`/admin`, to'liq mahsulot CRUD) + Telegram bot (`@moxaparfume_bot` — buyurtmalar/mahsulotlar/statistika, inline menyu)
- Webhook xavfsizligi — tasodifiy sir har server qayta ishga tushganda yangilanadi (`setWebhook`)
- UZ/RU/EN uch tilli vitrina, admin UZ-only

### Texnologiyalar

Sof Node.js 24 (`node:sqlite`, **0 npm dependency**) + vanilla JS/HTML/CSS. Dedikatsiyalangan `/opt/node24/` binary orqali ishlaydi (tizim node'i faqat v22). 15 avtomatik test (`npm test`).

### Konfiguratsiya

```env
PORT, HOST, PUBLIC_URL, ADMIN_EMAIL, ADMIN_PASSWORD, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DEMO_MODE, TRUST_PROXY, COOKIE_SECURE
```

### Fayllar

```
intim-shop-parfume/
├── server.mjs, package.json, migrations/001_initial.sql
├── .gitignore         — (.env, node_modules/, data/, coverage/ chetlab o'tadi)
├── lib/  bot.mjs, store.mjs, telegram.mjs
├── public/  index.html, admin.html, app.js, admin.js, style.css, admin.css, assets/*.svg
├── scripts/  reset-admin.mjs
├── tests/  bot.test.mjs, http.test.mjs, store.test.mjs
└── data/  store.sqlite (gitignored, jonli baza)
```

### Systemd va tarmoq

```
service: intim-shop-parfume
port:    127.0.0.1:8020
nginx:   https://intimshop.net (+www) — asosiy domen, SSL muddati 2027-01-07
         https://intimshop.narzullayev.com — eski manzil, endi faqat 301 redirect intimshop.net'ga
admin:   https://intimshop.net/admin
```

---

## 16. shifokor_yordamchisi

> "Шифокор ёрдамчиси" — ekhokardiografiya (yurak UTT) bo'yicha ta'lim/klinik-yordamchi platforma: shifokorlar, rezidentlar, tibbiyot talabalari uchun. Sotilishi rejalashtirilgan mahsulot. 2026-10-10/11'da qurilgan.

### Nima qiladi

- Kalkulyatorlar, qoidaga asoslangan qoralama xulosa + ixtiyoriy shifokor-tasdiqlash oqimi (`requireDoctorVerification` flag — admin panel orqali yoqilib/o'chirilishi mumkin, kod o'zgartirish shart emas)
- AI yordamchi chat (Claude) — **hozir ishlamayapti, umumiy Anthropic balansi tugagan**
- Obuna tariflari (UZS, hali narxlanmagan), to'liq UZ/RU/EN, WCAG AA dizayn-token tizimi
- **Admin override tizimi** — `config/app.json`dagi istalgan statik flag (testMode, paymentsEnabled, aiEnabled va h.k.) admin panel orqali jonli o'zgartirilishi mumkin, `GET /api/overrides` har doim HAQIQIY joriy holatni ko'rsatadi

### Texnologiyalar

Frontend: sof HTML/CSS/JS, build yo'q. Backend (`server/`): **0 npm dependency**, faqat Node built-in'lar (`node:http`, `fetch`, `node:crypto` WebCrypto PBKDF2), qo'lda yozilgan router/cookie/JSON-parser.

### Xavfsizlik

Alohida imtiyozsiz tizim useri `shifokor` (uid 999, root emas), systemd hardening (`NoNewPrivileges`, `ProtectSystem=strict`). Ma'lumotlar (parol xeshlari) **repo papkasidan tashqarida**, `/opt/shifokor_data/` (700/600 ruxsat, nginx web-root'dan tashqarida, `/server/` yo'liga `deny all`). HttpOnly+Secure+SameSite=Lax cookie sessiyalar, IP-asosli rate-limit.

**⚠️ Admin bootstrap qoidasi:** `cli.mjs` FAQAT server to'xtatilganda ishlatilishi kerak (`systemctl stop shifokor-server && node server/cli.mjs grant-admin <email> && systemctl start shifokor-server`) — ikkalasi bir vaqtda ishlasa, keyingi yozuv avvalgisini jim-jit ezib yuboradi (fayl-asosli store).

### Konfiguratsiya

`.env` repo papkasida YO'Q — server sirlari `/opt/shifokor_data/server.env`da:
```env
PORT, DATA_DIR, ANTHROPIC_API_KEY, ANTHROPIC_MODEL
```

### Fayllar

```
shifokor_yordamchisi/
├── index.html
├── css/  base.css, tokens.css
├── js/
│   ├── app.js, theme-init.js
│   ├── core/  calc.js, config.js, policy.js, rules.js, service.js, store.js, thresholds.js, ...
│   ├── api/, ui/, views/
├── data/  cases/, formulas/, i18n/, navigation.json, parameters.json, plans.json,
│          providers.json, rules.json, sources.json, specialties.json, thresholds.json
├── config/app.json
├── assets/  diagrams/, icons/
└── server/  cli.mjs, context.mjs, index.mjs
```

### Systemd va tarmoq

```
service: shifokor-server
port:    127.0.0.1:8030 (node, user=shifokor)
nginx:   https://shifokor.narzullayev.com — SSL muddati 2027-01-08
```

---

## 17. moxa_taplink

> "Moxa Parfume" brendi uchun link-in-bio sahifa — `taplink.cc/moxaparfume`ning o'rnini bosuvchi, xuddi shu brend/egasi (`intim-shop-parfume`dagi @moxaparfume1/@moxaparfume bilan bir xil). 2026-10-13'da qurilgan.

### Nima qiladi

Statik sahifa: Telegram/Instagram/Telegram kanal/intimshop.net havolalari, "18+" ogohlantirish. Vino-qizil+oltin dizayn (Playfair Display+Jost shriftlar, haqiqiy brend logotipi asosida), ambient "mist" canvas animatsiyasi, faqat qorong'i rejim.

### Texnologiyalar

Sof statik HTML/CSS/JS — backend, dependency, build jarayoni yo'q.

### Fayllar

```
moxa_taplink/
├── index.html
└── avatar.jpg
```

### Tarmoq

```
nginx: https://moxa.intimshop.net — SSL muddati 2027-01-10, systemd xizmat shart emas (statik)
```

---

## 18. allmax-fixprice

> To'liq onlayn-do'kon — ALLMAX Fix Price erkaklar kiyim-kechak katalogi, buyurtma va Telegram bot admin. `intim-shop-parfume` (bo'lim 15) bilan bir xil arxitektura/andoza. 2026-10-15'da qurilgan va shu kuni domeni (`fixprice.org`, Namecheap, `addPeriod` ichida ro'yxatdan o'tgan) ulangan — **bu session tomonidan emas**, serverda tayyor holda topilgan (git tarixi + fayl vaqt belgilari buni tasdiqlaydi). ⚠️ **Bu bo'lim boshqa 17 tasidan YENGILROQ tekshiruv asosida yozilgan** — kod qator-baqator o'qilmagan, faqat tuzilma/konfiguratsiya/systemd tashqaridan tekshirilgan. Keyingi chuqur tekshiruvda to'liq qayta tasdiqlang.

### Nima qiladi

Mahsulot katalogi (14 kategoriya: kurtka, ko'ylak, kardigan, futbolka, shim, kostyum, dvoyka, gilet, oyoq-kiyim, remen, hamyon, sumka, aksessuar, vetrovka), savat/buyurtma oqimi, admin panel (`/admin`) va Telegram bot orqali mahsulot/buyurtma boshqaruvi.

⚠️ **Nomuvofiqlik topildi:** `.env`da `DEMO_MODE=false`, lekin repodagi `ASSETS.md` hali ham "barcha mahsulot rasmlari — placeholder SVG belgi, haqiqiy foto yo'q" deb yozilgan (xuddi `intim-shop-parfume` o'zining haqiqiy fotolari bilan almashtirilgunga qadar bo'lgani kabi). Demo rejim o'chirilgan, lekin katalogda haqiqiy mahsulot foto bor-yo'qligi `/admin` panelidan tasdiqlanmagan — ehtiyot bo'lib ishlating.

### Texnologiyalar

Sof Node.js 24 (`node:sqlite`, **npm dependency yo'q**) + vanilla JS/HTML/CSS, build jarayoni yo'q — `intim-shop-parfume`ning aynan o'zi uslubida. Dedikatsiyalangan `/opt/node24/` binary orqali ishlaydi.

### Konfiguratsiya

```env
PORT, HOST, PUBLIC_URL, ADMIN_EMAIL, ADMIN_PASSWORD, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DEMO_MODE, TRUST_PROXY, COOKIE_SECURE
```

### Fayllar

```
allmax-fixprice/
├── server.mjs, package.json, migrations/001_initial.sql
├── lib/  store.mjs, telegram.mjs, bot.mjs
├── scripts/  reset-admin.mjs
├── tests/  http.test.mjs, bot.test.mjs, store.test.mjs
├── public/
│   ├── index.html, app.js, style.css        — mijoz vitrinasi
│   ├── admin.html, admin.js, admin.css      — admin panel
│   ├── brand.json                            — ✅ 2026-10-15 kech: haqiqiy Telegram/Instagram/manzil to'ldirildi
│   └── assets/  mark.png, lockup-on-white.png — haqiqiy ALLMAX logotip fayllari, 14 ta kategoriya SVG ikonkasi
└── data/  store.sqlite (gitignored, jonli baza)
```

### Systemd va tarmoq

```
service: allmax-fixprice — ✅ active, 0 restart, ~37 MB RAM
         ExecStart=/opt/node24/bin/node server.mjs, 127.0.0.1:8040 (tashqaridan yopiq)
nginx:   https://fixprice.org (+www) → proxy_pass http://127.0.0.1:8040/, SSL muddati 2027-01-13
```

---

## 19. allmax_taplink

> Allmax Fix Price uchun link-in-bio sahifa — `taplink.cc/allmax.fixprice`ning o'rnini bosuvchi (`moxa_taplink`, bo'lim 17, bilan bir xil g'oya). **18-bo'limdagi `allmax-fixprice` to'liq do'konidan ALOHIDA loyiha** — ikkalasi bir domen oilasida (`fixprice.org`) birga turadi: tub domen = to'liq do'kon, `allmax.` subdomeni = ushbu havolalar sahifasi. 2026-10-15'da shu sessiyada qurilgan.

### Nima qiladi

Statik "narx yorlig'i" (price-tag) dizaynidagi sahifa: logotip medalyoni (haqiqiy ALLMAX "X" belgisi, 3D porlash animatsiyasi va sichqoncha ustida tilt effekti bilan), Telegram/Tik Tok/YouTube/Instagram havolalari, do'kon manzili + 24/7 shtamp-belgisi, Google Xaritalar tugmasi. Barcha kontent (havolalar, manzil, soat) `taplink.cc/allmax.fixprice`ning o'z `window.data` JSON blokidan 1:1 olingan (o'sha manzil/soat ma'lumoti eskirgan deb belgilangan edi — endi shu orqali tasdiqlandi, `company_allmax` xotira faylida yangilandi).

### Texnologiyalar

Sof statik HTML/CSS — backend, dependency, build jarayoni yo'q. Shriftlar (Bebas Neue, Manrope, Oswald) `fonts/`da mahalliy `.woff2` fayllar sifatida (Google Fonts'dan bir martalik yuklab olingan, runtime'da tashqi chaqiruv yo'q).

### Fayllar

```
allmax_taplink/
├── index.html
├── mark.png              — haqiqiy ALLMAX "X" belgisi (allmax-fixprice/public/assets/mark.png bilan bir xil fayl)
└── fonts/                — 12 ta .woff2 (3 shrift oilasi × vazn × latin/latin-ext)
```

### Tarmoq

```
nginx: https://allmax.fixprice.org — SSL muddati 2027-01-13, systemd xizmat shart emas (statik)
```

---

# Infratuzilma

## Server holati (2026-10-14 jonli tekshiruv, + 2026-10-15 qo'shimcha qator)

| Servis | Holat | Port | Bot / Domen | RAM |
|---|---|---|---|---|
| `allmax-fixprice` | ✅ active, 0 restart | 127.0.0.1:8040 | fixprice.org | 37 MB |
| `allmax-dashboard` | ✅ active, 0 restart | 8080 (ichki) | — | 34 MB |
| `allmax-food-order-bot` | ✅ active, 0 restart | — | @food_control_rBot | 145 MB |
| `bitrix-lead-alert-bot` | ✅ active, 0 restart | 8000 (tashqi yopiq) | — | 72 MB |
| `feedback-bot` | ✅ active, 0 restart | — | @allmax_feedback_bot | 119 MB |
| `food-control-bot` | ✅ active, 0 restart | — | @ovqatnazoratiuzbot | 137 MB |
| `marketing-task-control-bot` | ✅ active, 0 restart | — | @allmax_vazifalarbot | 94 MB |
| `ozish-backend` | ✅ active, 0 restart | 127.0.0.1:8010 | narzullayev.com/ozish-api/ | 91 MB |
| `moliya-bot` | ✅ active, 0 restart | — | @meningbugalterimbot | 692 MB |
| `intim-shop-parfume` | ✅ active, 0 restart | 127.0.0.1:8020 | intimshop.net | 49 MB |
| `shifokor-server` | ✅ active, 0 restart | 127.0.0.1:8030 | shifokor.narzullayev.com | 16 MB |
| `allmax-telethon` | ⏸ disabled, inactive | — | @allmaxshaxsiy (biznes) | — |
| `telegram-ai-assistant` | ⏸ disabled, inactive | — | @Claude_ai_oBot | — |
| `allmax-instagram-agent` | ⏸ disabled, inactive | 8002 | — | — |
| `allmax-hr-bot` | ⏸ disabled, inactive | — | @allmax_jbot | — |
| `instagram-dm-lead-bot` | 🗑 orphan unit, papka yo'q | — | — | — |

Barchasi `systemctl enable`, `Restart=always` (allmax-hr-bot bundan mustasno). `systemctl --failed` — toza. `systemctl list-unit-files --state=enabled` to'liq filtrsiz ro'yxatda begona xizmat yo'q.

## Nginx (8 ta domen)

| URL | Backend | Holat |
|---|---|---|
| `fixprice.org` (+www) | `127.0.0.1:8040` | ✅ Jonli, `allmax-fixprice`ga proxy |
| `allmax.fixprice.org` | Statik fayllar | ✅ `allmax_taplink` |
| `allmax.tizm.uz/dashboard/` | `127.0.0.1:8080` | ✅ Jonli, `allmax_dashboard`ga proxy |
| `allmax.tizm.uz/instagram/` | — | `410 Gone` (statik, so'rov hajmi ~99.8% pasaygan) |
| `allmax.tizm.uz/tirox/` | — | O'lik portga proxy, kuniga ~2 so'rov, muhim emas |
| `narzullayev.com` (+www) | Statik fayllar | ✅ `narzullo_portfolio` |
| `narzullayev.com/ozish-api/` | `127.0.0.1:8010` | ✅ `ozish_backend`ga proxy |
| `intimshop.net` (+www) | `127.0.0.1:8020` | ✅ `intim-shop-parfume`ga proxy |
| `intimshop.narzullayev.com` | — | 301 → `intimshop.net` (eski manzil, faqat link buzilmasligi uchun) |
| `moxa.intimshop.net` | Statik fayllar | ✅ `moxa_taplink` |
| `shifokor.narzullayev.com` | `127.0.0.1:8030` | ✅ `shifokor-server`ga proxy |

`nginx -t` — toza.

## SSL sertifikatlari (Let's Encrypt, certbot.timer orqali avto-yangilanadi)

| Domen | Muddati |
|---|---|
| allmax.fixprice.org | 2027-01-13 |
| fixprice.org (+www) | 2027-01-13 |
| allmax.tizm.uz | 2027-01-04 |
| intimshop.narzullayev.com | 2027-01-07 |
| intimshop.net (+www) | 2027-01-07 |
| moxa.intimshop.net | 2027-01-10 |
| narzullayev.com (+www) | 2026-12-16 |
| shifokor.narzullayev.com | 2027-01-08 |

## Firewall (UFW)

Faol, default-deny incoming: faqat 22 (SSH), 80, 443 ochiq. Boshqa barcha port — eski (8000, 8080) va yangi (8010, 8020, 8030) — faqat `127.0.0.1`da tinglaydi, tashqaridan UFW+bind-address ikkalasi bilan yopiq.

## Git / GitHub

```bash
cd /opt/AllmaxProjects
git add <fayllar>
git commit -m "o'zgarish tavsifi"
git push origin master
```
Repo **public**: [github.com/alishex/projects](https://github.com/alishex/projects). 0 ahead/0 behind. **2026-10-15'dan boshlab barcha 19 loyiha git-backed** (5 tasi — `intim-shop-parfume`, `moliya_bot`, `moxa_taplink`, `ozish_backend`, `shifokor_yordamchisi` — 2026-10-14'gacha umuman kuzatilmagan edi; `allmax_taplink` shu kuni (10-15) qo'shildi — `allmax-fixprice` 10-15'ning o'zida boshqa joydan allaqachon commit qilingan holda topildi). **Muhim: `.env.example` fayllariga hech qachon haqiqiy qiymat yozmang** — bu fayllar odatda git'ga tushadi va public repoga push bo'ladi (2026-08-08'da ikkita loyihada aynan shu xato topilgan, hali ham to'liq tuzatilmagan — yuqoridagi xavfsizlik bo'limiga qarang). **Bu repoga yaratiladigan commit'larga hech qachon "Co-Authored-By: Claude" yoki shunga o'xshash trailer qo'shilmasin** — bu standart amaliyot (2026-08-08'da butun git tarixi aynan shu sababdan qayta yozilgan).

## Loglarni ko'rish

```bash
journalctl -u <service-name> -f          # Real vaqtda
journalctl -u <service-name> -n 50       # Oxirgi 50 qator
grep Accepted /var/log/auth.log          # SSH login tarixi (last -a ISHONCHSIZ, ishlatmang)
```

## Barcha faol servislarni qayta ishga tushirish

```bash
systemctl restart allmax-dashboard allmax-food-order-bot bitrix-lead-alert-bot \
  feedback-bot food-control-bot marketing-task-control-bot allmax-fixprice \
  ozish-backend moliya-bot intim-shop-parfume shifokor-server
```

## Deploy qilish (yangi/yangilangan loyiha)

```bash
rsync -avz --exclude venv --exclude __pycache__ --exclude .env --exclude "*.session" --exclude node_modules \
  ./loyiha/ root@209.38.239.245:/opt/AllmaxProjects/loyiha/
ssh allmaxhamkor-do "cd /opt/AllmaxProjects/loyiha && venv/bin/pip install -r requirements.txt && systemctl restart <service>"
```

## Utility skriptlar

| Fayl | Tavsif |
|---|---|
| `delete_tirox_leads.py` | Bitrix24'da TIROX integratsiyasi orqali tushgan leadlarni topib o'chiradi |
| `deploy.sh` | Umumiy deploy skripti |

---

*ALLMAX — Avtomatlashtirish va raqamli transformatsiya. Bu hujjat 2026-10-14'da jonli server holati asosida to'liq qayta yozildi — 55 kunlik tanaffusdan keyingi "noldan tubdan" tekshiruv asosida (oldingi to'liq qayta yozish: 2026-08-08). Asosiy o'zgarishlar: 5 ta yangi shaxsiy loyiha hujjatlandi va git'ga qo'shildi (`ozish_backend`, `moliya_bot`, `intim-shop-parfume`, `shifokor_yordamchisi`, `moxa_taplink`), umumiy Anthropic balansi yana tugagani va Instagram webhook to'foni deyarli tugagani qayd etildi, barcha RAM/port/SSL/nginx ma'lumotlari jonli holatga yangilandi. **2026-10-15: 2 ta yangi bo'lim (18-allmax-fixprice, 19-allmax_taplink) qo'shildi** — bu to'liq qayta yozish emas, faqat qo'shimcha; bo'lim 18 yengilroq tekshiruv asosida yozilgan, belgilab qo'yilgan. Oldingi versiyalar singari, bu hujjat ham vaqt o'tishi bilan eskiradi — load-bearing tafsilotlarni doim jonli kod/systemd/git holati bilan solishtirib tekshiring.*
