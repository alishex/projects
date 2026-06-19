# ALLMAX Projects

**ALLMAX** kompaniyasining barcha avtomatlashtirish loyihalari — Telegram botlar, Instagram integratsiya, CRM, AI yordamchilar va HR tizimlar.

**Server:** DigitalOcean VPS — Ubuntu 24.04 — `209.38.239.245` — 2 vCPU / 4 GB RAM (s-2vcpu-4gb)
**AI:** Anthropic Claude `claude-opus-4-8` (barcha loyihalarda asosiy model)
**GitHub:** [alishex/projects](https://github.com/alishex/projects)

---

## Loyihalar ro'yxati

| # | Loyiha | Tavsif | Port | RAM |
|---|---|---|---|---|
| 1 | [allmax_telethon](#1-allmax_telethon) | Telegram DM Community Agent — Claude AI auto-reply + MoySklad + Bitrix24 | — | ~310 MB |
| 2 | [allmax_hr_bot](#2-allmax_hr_bot) | HR onboarding, AI intervyu, reglament, Clockster | — | ~170 MB |
| 3 | [feedback_bot](#3-feedback_bot) | Mijoz fikr-mulohaza yig'ish boti | — | ~130 MB |
| 4 | [bitrix_lead_alert_bot](#4-bitrix_lead_alert_bot) | Bitrix24 yangi lead → Telegram guruh alert | 8000 | ~70 MB |
| 5 | [marketing_task_control_bot](#5-marketing_task_control_bot) | Marketing jamoasi vazifalar + grafik hisobotlar | — | ~115 MB |
| 6 | [instagram_bitrix_dm_lead_bot](#6-instagram_bitrix_dm_lead_bot) | Instagram DM → Bitrix24 CRM + Project → Telegram | 8002 | ~80 MB |
| 7 | [telegram_ai_assistant](#7-telegram_ai_assistant) | Claude AI shaxsiy Telegram akkaunt assistenti | — | ~860 MB |
| 8 | [allmax_ai_assistant](#8-allmax_ai_assistant) | Claude AI ALLMAX akkaunt assistenti | — | ~220 MB |

---

## 1. allmax_telethon

> ALLMAX Telegram DM Community Agent — Claude AI yordamida mijozlar bilan avtomatik suhbat, buyurtma yig'ish, MoySklad stok tekshiruvi va Bitrix24 integratsiya.

### Nima qiladi

**Community Agent (asosiy rejim):**
1. Telegram DM ga kelgan **matn, ovoz (golos), round video, video, rasm, GIF, stiker** xabarlarni qabul qiladi
2. Claude AI oxirgi **30 kunlik to'liq suhbat tarixini** tahlil qilib javob beradi
3. Mijoz qaysi tilda yozsa — **shu tilda** javob beradi (O'zbek / Rus / Ingliz)
4. Standart savollarga (manzil, narx, o'lcham, yetkazib berish, ish vaqti) avtomatik javob beradi
5. **MoySklad** dan real vaqtda showroom mahsulot mavjudligi va narxini tekshiradi (`check_stock` tool)
6. Imlo xatosi yoki sinonim aniqlasa qayta qidiradi: `remen` → `kamar`, `badaj` → `bandaj`
7. Buyurtma ma'lumotlarini tabiiy suhbat orqali yig'adi (9 ta maydon)
8. Buyurtma to'liq bo'lganda **Bitrix24 CRM lead + Projects task** yaratadi
9. **Operator guruhiga** buyurtma xulasasi + Telegram havolasi yuboradi
10. Murakkab savollarda operatorga yo'naltiradi
11. Mijoz ism + telefon yozsa — to'liq buyurtma kutmasdan **Bitrix24 Project task** ochadi
12. Har kuni **00:00 UZT** da guruhga kunlik hisobot yuboradi (kimlar yozdi, nima haqida, nechta)

**Fallback rejim (Community Agent o'chirilganda):**
- Mijozdan ism va telefon so'raydi
- Bitrix24 ga lead yaratadi

### Media xabarlarni qayta ishlash

| Media turi | Ishlov |
|---|---|
| Ovoz (golos) | faster-whisper → matn (o'zbek til, language="uz") |
| Round video | faster-whisper → matn (o'zbek til) |
| Video | faster-whisper → matn |
| Rasm | Claude Vision (base64, SQLite cache) |
| GIF | Birinchi kadr JPEG → Claude Vision (SQLite cache) |
| Stiker (WebP) | Claude Vision (SQLite cache) |
| Animated stiker (.tgs) | O'tkazib yuboriladi |

**WebM/OGG muammosi yechilgan:** Telegram ovoz xabarlari `.webm` kengaytmali lekin aslida OggS format bo'ladi. Magic bytes orqali haqiqiy format aniqlanib ffmpeg ga to'g'ri `-f ogg` beriladi.

### Buyurtma yig'ish (9 ta maydon)

| # | Maydon | Tavsif |
|---|---|---|
| 1 | ism | Mijoz ismi |
| 2 | telefon | Raqami |
| 3 | mahsulot | Nomi yoki tavsifi |
| 4 | razmer | O'lcham (M–3XL, shim 29–56) |
| 5 | rang | Rang |
| 6 | soni | Dona soni |
| 7 | viloyat | Yetkazib berish viloyati |
| 8 | tuman | Tuman |
| 9 | pochta | BTS / EMU / UzPost / YandexGo |

### MoySklad integratsiya

- Showroom ombori filtri — faqat mavjud mahsulotlar ko'rsatiladi (`stock > 0`)
- 1989 ta mahsulot, paginatsiya limit=1000
- **Local cache 600 soniya** (10 daqiqa) — har so'rovda 3 soniya sarflanmaydi
- Startup da prewarm: servis ishga tushganda darhol yuklanadi
- Sotuvdagi narx (`salePrice`) ko'rsatiladi, kirish narxi emas
- Top 15 ta natija qaytariladi (avval 8 edi)

### Do'kon ma'lumotlari (agent biladi)

| | |
|---|---|
| **Manzil** | Toshkent, Bunyodkor Savdo Majmuasi (Korzinka 1-qavat), metro: Mirzo Ulug'bek |
| **Telefon** | +998 78 555 31 31 |
| **Do'kon ish vaqti** | **24/7** — hech qachon yopilmaydi |
| **Call centre / Community** | Har kuni **09:30–22:00** |
| **Narx bosqichlari** | 99 000 / 149 900 / 199 900 / 249 900 / 299 900 / Premium |
| **To'lov** | Naqd, plastik, Uzum nasiya |
| **Yetkazib berish (viloyatlar)** | BTS (Nukus, Urganch, Buxoro, Navoiy, Samarqand, Qarshi, Termiz, Farg'ona, Namangan, Andijon, Guliston, Jizzax), EMU, UzPost |
| **Yetkazib berish (Toshkent shahri)** | YandexGo kuryer (manzil va vaqtni operator kelishib oladi) |
| **Almashtirish/qaytarish** | Mumkin (batafsil operator aytadi) |

### Qanday ishlaydi

```
Yangi DM (matn/ovoz/video/rasm/GIF/stiker)
        │
  Burst collector (1.8 soniya — ketma-ket xabarlarni birlashtiradi, maks 5 ta)
        │
  build_chat_history()
    ├─ 30 kun matn tarixi (oxirgi 60 xabar)
    ├─ 48 soat ovoz/round video/video → faster-whisper transkriptsiya (o'zbek til)
    └─ so'nggi 3 ta rasm + GIF + stiker → Claude Vision (SQLite cache)
        │
  CommunityAgent.process() — Claude API (agentic loop, maks 4 iteratsiya)
    ├─ check_stock tool     → moysklad.py → showroom stok + narx → tool_result
    ├─ order_complete tool  → Bitrix24 CRM lead + Projects task + guruh xabar
    ├─ needs_human tool     → operator guruhiga yo'naltirish
    └─ oddiy javob          → mijozga yuboriladi (uz/ru/en)
        │
  _try_auto_contact_task() — ism+telefon aniqlansa Bitrix24 Project task
        │
  _save_daily_contact()    → SQLite analytics DB (kunlik hisobot uchun)
```

### Tezlik optimizatsiyalari

| Optimizatsiya | Natija |
|---|---|
| MoySklad cache TTL 600s | Cache miss faqat 10 daqiqada 1 marta (avval har daqiqada) |
| Rasm/GIF SQLite cache | Bir marta yuklab — keyingi so'rovlarda 0ms |
| Whisper prewarm startup da | Birinchi ovoz xabarida 0ms cold start (avval ~8s) |
| MoySklad prewarm startup da | Birinchi stok so'rovida 0ms cold start (avval ~3s) |

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `telethon` | Telegram user-account client (`allmax_cm_session`) |
| `anthropic` | Claude AI `claude-opus-4-8` — Community Agent (tool-use, agentic loop) |
| `faster-whisper` | Ovoz/video transkriptsiya (`base` model, `language="uz"`, `beam_size=5`) |
| `ffmpeg` | Audio ajratish (WebM/OGG format detection by magic bytes) |
| `sqlite3` | Analytics DB + media transcription cache + image cache |
| `requests` | Bitrix24 API so'rovlari |
| `urllib` | MoySklad REST API (gzip encoding majburiy) |
| `python-dotenv` | .env konfiguratsiya |

### Konfiguratsiya (.env)

```env
# Telegram
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
PHONE_NUMBER=+998...
SESSION_NAME=allmax_cm_session
ANTHROPIC_MODEL=claude-opus-4-8

# Community Agent
COMMUNITY_AGENT_ENABLE=true
COMMUNITY_ADDRESS=Toshkent sh., Bunyodkor Savdo Majmuasi ...
COMMUNITY_PHONE=+998 78 555 31 31
COMMUNITY_WORK_START=9
COMMUNITY_WORK_END=22
COMMUNITY_HISTORY_LIMIT=60
COMMUNITY_HISTORY_DAYS=30
COMMUNITY_MEDIA_HOURS=48
LEAD_GROUP=-1003879594278

# Burst collector
MESSAGE_BURST_WINDOW=1.8
MAX_BURST_MESSAGES=5
MIN_REPLY_INTERVAL=0.8

# MoySklad
MOYSKLAD_TOKEN=...

# Bitrix24 CRM
BITRIX_ENABLE=true
BITRIX_WEBHOOK_URL=https://allmax.bitrix24.kz/rest/63/.../
BITRIX_ASSIGNED_BY_ID=1
BITRIX_LEAD_TITLE_PREFIX=TELEGRAM
BITRIX_SOURCE_ID=TELEGRAM

# Bitrix24 Projects (Zadachi)
BITRIX_PROJECT_ENABLE=true
BITRIX_PROJECT_GROUP_ID=15
BITRIX_PROJECT_RESPONSIBLE_ID=63
BITRIX_PROJECT_STAGE_ID=301
BITRIX_PROJECT_TASK_DEADLINE_HOURS=0
BITRIX_PROJECT_BIND_TO_CRM=true
```

### Fayllar

| Fayl | Vazifasi |
|---|---|
| `main_ready_project.pyw` | Asosiy bot: event handler, burst collector, Bitrix integratsiya, daily report |
| `community_agent.py` | Claude AI Community Agent: system prompt, tool-use, agentic loop, ko'p til |
| `moysklad.py` | MoySklad REST API: showroom stok fetch, local cache 600s, prewarm |
| `media_handler.py` | Media: audio extraction (OGG/WebM), Whisper transkriptsiya, rasm/GIF/stiker encode, SQLite cache |

### Systemd

```
service:      allmax-telethon
user-session: @allmaxshaxsiy (ID: 6586004680)
session file: allmax_cm_session.session
```

---

## 2. allmax_hr_bot

> ALLMAX kompaniyasi uchun to'liq HR avtomatlashtirish tizimi — vakansiyalardan yakuniy testgacha.

### Nima qiladi

1. **Ariza qabul qilish** — nomzod `/start` bosadi, tizim unga mavjud vakansiyalarni ko'rsatadi
2. **Reglament yuborish** — vakansiya tanlangach nomzodga tegishli DOCX reglament avtomatik yuboriladi
3. **AI intervyu** — Claude AI (GPT-5 o'rniga OpenAI ishlatiladi) nomzodga savollar beradi va javoblarni baholaydi
4. **Rezyume tahlili** — PDF/DOCX rezyumeni AI tahlil qilib ball beradi
5. **7 kunlik stajirovka** — darslar, testlar, materiallar ketma-ketligi
6. **Clockster integratsiya** — yakuniy test tugagach davomat tizimiga ulanadi
7. **Export** — natijalar PDF va Excel formatida eksport qilinadi
8. **Follow-up** — intervyudan keyingi avtomatik xabarlar
9. **Admin panel** (`/admin`) — vakansiyalar, reglamentlar, darslar, testlarni Telegram orqali boshqarish (kod o'zgartirmasdan)

### Admin panel imkoniyatlari

- Yangi vakansiya qo'shish / o'chirish
- DOCX reglamentni almаshtirish (fayl yuborish orqali)
- Yangi dars / test / material qo'shish
- Nomzodlar ro'yxati va holatlari

### Qanday ishlaydi

```
Nomzod /start → Vakansiyalar ro'yxati → Tanlash
    → Reglament yuborish (DOCX)
    → AI Intervyu (OpenAI GPT-5, JSON structured output)
    → Rezyume yuklab tahlil (PDF/DOCX → AI ball)
    → 7 kunlik stajirovka (darslar + testlar)
    → Yakuniy test
    → Clockster ga ulanish (davomat)
    → PDF/Excel eksport
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Telegram Bot API, FSM state machine |
| `anthropic` / `openai` | AI intervyu va rezyume baholash (GPT-5, JSON structured) |
| `aiosqlite` | Async SQLite — nomzodlar, vaziyatlar, testlar |
| `apscheduler` | Avtomatik vazifalar (follow-up, reminder) |
| `python-docx` | DOCX reglament va eksport |
| `pypdf` | PDF rezyume o'qish |
| `reportlab` | PDF eksport generatsiya |
| `openpyxl` | Excel eksport |
| `python-dotenv` | .env konfiguratsiya |

### Konfiguratsiya (.env)

```env
BOT_TOKEN=...                    # @allmax_jbot tokeni
ANTHROPIC_API_KEY=...            # Claude AI (zaxira)
OPENAI_API_KEY=...               # Asosiy AI model
OPENAI_MODEL=gpt-5.5
OPENAI_REASONING_EFFORT=high
ADMIN_IDS=1667797265,8148326552  # Admin Telegram ID lari (vergul bilan)
DB_PATH=data/database.db
EXPORT_DIR=exports
TIMEZONE=Asia/Tashkent
REGULATIONS_DIR=reglamentlar
DEFAULT_SHOP_ADDRESS=Toshkent shaxri Chilonzor tumani, metro Mirzo Ulug'bek, Bunyodkor Korzinka
DEFAULT_BRANCH=ALLMAX
CLOCKSTER_ENABLED=false          # Yakuniy test tugagach true qilinadi
CLOCKSTER_API_BASE=https://api.clockster.com/company/v2/
CLOCKSTER_SYNC_INTERVAL_MINUTES=15
```

### Fayllar tuzilmasi

```
allmax_hr_bot/
├── main.py                     — Ishga tushirish nuqtasi
├── app/
│   ├── bot.py                  — Bot va Dispatcher sozlash
│   ├── config.py               — .env sozlamalar
│   ├── database.py             — SQLite schema va so'rovlar
│   ├── states.py               — FSM holatlari
│   ├── handlers/
│   │   ├── start.py            — /start, salomlashuv
│   │   ├── vacancies.py        — Vakansiyalar
│   │   ├── resume.py           — Rezyume qabul va tahlil
│   │   ├── interview.py        — AI intervyu
│   │   ├── onboarding.py       — 7 kunlik stajirovka
│   │   ├── admin.py            — Statik admin buyruqlari
│   │   ├── dynamic_admin.py    — Dinamik admin panel (vakansiya/reglament boshqaruv)
│   │   └── followup.py         — Intervyudan keyingi harakatlar
│   └── services/
│       ├── scheduler_service.py — APScheduler vazifalar
│       ├── dynamic_service.py   — Dinamik katalog bootstrap
│       └── clockster_service.py — Clockster API integratsiya
├── reglamentlar/               — DOCX reglament fayllari
└── data/database.db            — SQLite baza
```

### Systemd

```
service: allmax-hr-bot
bot:     @allmax_jbot
```

---

## 3. feedback_bot

> Mijozlardan baho va fikr-mulohaza yig'ish boti — 1 dan 5 gacha reyting + media qabul qiladi.

### Nima qiladi

1. Mijoz `/start` bosadi — bot ularni salomlaydi va baho berishni so'raydi
2. Mijoz **1 dan 5 gacha baho** beradi (inline tugmalar orqali)
3. Matn sharh, rasm, video, ovoz xabar qabul qiladi
4. Barcha fikr-mulohazalar **admin chat ga** paket shaklida yuboriladi
5. Ma'lumotlar **JSON faylda** atomik yozish bilan saqlanadi (race condition himoyasi)

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Telegram Bot API |
| `python-dotenv` | .env konfiguratsiya |

### Konfiguratsiya (.env)

```env
BOT_TOKEN=...          # @allmax_feedback_bot tokeni
ADMIN_CHAT_ID=...      # Feedback yuboriluvchi admin chat/guruh ID
```

### Fayllar

```
feedback_bot/
├── bot.py              — Asosiy bot va polling
├── config.py           — BOT_TOKEN, ADMIN_CHAT_ID
├── states.py           — FSM holatlari
├── handlers/
│   ├── start.py        — /start, kirish
│   └── feedback.py     — Baho va sharh qabul qilish
├── keyboards/          — Inline klaviatura (1–5 reyting)
└── storage/            — JSON feedback saqlash
```

### Systemd

```
service: feedback-bot
bot:     @allmax_feedback_bot
```

---

## 4. bitrix_lead_alert_bot

> Bitrix24 CRM ga yangi lead tushganda Telegram guruhiga darhol xabar yuboradi va mas'ul odamni mention qiladi.

### Nima qiladi

1. **Webhook** — Bitrix24 dan lead tushganda darhol signal oladi (real-time)
2. **Backup polling** — har 1 daqiqada Bitrix24 ni tekshiradi (webhook o'tkazib yuborilsa)
3. Yangi lead aniqlanganda **formatlangan xabar** + mas'ul shaxsni **@mention** qilib guruhga yuboradi
4. **Checkpoint tizimi** — bir lead ikki marta yuborilmaydi (SQLite)
5. Birinchi ishga tushganda eski leadlarni yubormaйdi — faqat undan keyingilari
6. Lead ichida ism bo'lmasa, bog'langan contactdan ism/telefon/email olishga urinadi
7. Telegram `429 Too Many Requests` holatida `retry_after` vaqtini kutadi

### Qanday ishlaydi

```
Bitrix24 lead tushdi
    │
    ├─ Webhook (darhol) → FastAPI POST /webhook → processor.py
    │
    └─ Backup polling (har 1 daqiqa) → bitrix.py → yangi leadlar tekshiruv
           │
       SQLite checkpoint — yuborilganmi?
           │ Yo'q
       Telegram guruhga xabar + @Mukhtarov A'lo mention
           │
       Checkpoint yangilanadi (lead_id saqlandi)
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `fastapi` | Webhook endpointi (`POST /webhook`) |
| `uvicorn` | ASGI server |
| `apscheduler` | Har daqiqa backup polling |
| `aiosqlite` | Checkpoint saqlash |
| `httpx` | Bitrix24 API + Telegram Bot API so'rovlari |
| `python-dotenv` | .env konfiguratsiya |

### Konfiguratsiya (.env)

```env
# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=-1003963026499
TELEGRAM_MENTION_USER_ID=848809437
TELEGRAM_MENTION_NAME=Mukhtarov A'lo
TELEGRAM_MIN_DELAY_SECONDS=1.2

# Bitrix24
BITRIX_WEBHOOK_BASE_URL=https://allmax.bitrix24.kz/rest/1/.../
BITRIX_PORTAL_URL=https://allmax.bitrix24.kz

# Rejim
REALTIME_ONLY_MODE=true
POLL_SEND_UNKNOWN_ON_START=false
```

### Fayllar

```
bitrix_lead_alert_bot/
├── run.py                    — Ishga tushirish
├── app/
│   ├── main.py               — FastAPI endpointlar
│   ├── bitrix.py             — Bitrix24 REST API client
│   ├── telegram_client.py    — Telegram Bot API + rate limit himoya
│   ├── processor.py          — Lead yuborish va retry logikasi
│   ├── scheduler.py          — Backup polling
│   ├── database.py           — SQLite + realtime checkpoint
│   ├── config.py             — .env sozlamalar
│   └── lead_utils.py         — Lead/contact parsing, xabar formatlash
└── scripts/get_chat_id.py    — Chat ID aniqlash utility
```

### Systemd

```
service: bitrix-lead-alert-bot
port:    8000
```

---

## 5. marketing_task_control_bot

> Marketing jamoasi uchun vazifa berish, nazorat qilish va **Eisenhower matritsasi** ko'rinishida grafik hisobot tizimi.

### Nima qiladi

1. **Admin** Telegram orqali vazifa yaratadi va xodimga tayinlaydi
2. **Xodim** deadline taklif qiladi, admin tasdiqlaydi yoki o'zgartiradi
3. Avtomatik **24 soat, 3 soat, 1 soat** oldin reminder yuboriladi
4. Muddat o'tsa — **overdue** ogohlantirish
5. Xodim **bajarilgan** deb belgilaydi
6. Admin va xodim uchun **Eisenhower matritsasi** shabloniga yozilgan **PNG grafik** hisobot
7. Tarix, arxiv, statistika

### Holatlar

```
ACTIVE → COMPLETED
ACTIVE → OVERDUE (deadline o'tsa)
ACTIVE → CANCELLED (admin bekor qilsa)
```

### Grafik hisobot

Shablon: `assets/toliq_ish_vazifalar_template.png` (Eisenhower matritsasi)
- Har safar shablonning nusxasidan foydalaniladi (original o'zgarmaydi)
- Vazifa matnlari va deadlinelar mavjud rangli kataklarga yoziladi
- 5 dan ko'p vazifa bo'lsa keyingi sahifa yaratiladi

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Telegram Bot API, FSM |
| `aiosqlite` | Vazifalar bazasi |
| `apscheduler` | Reminder va overdue tekshirish |
| `Pillow` | PNG grafik hisobot generatsiya |
| `python-dotenv` | .env konfiguratsiya |

### Konfiguratsiya (.env)

```env
BOT_TOKEN=...           # @allmax_vazifalarbot tokeni
ADMIN_ID=...            # Admin Telegram user ID
TIMEZONE=Asia/Tashkent
DATABASE_PATH=database/tasks.db
```

### Fayllar

```
marketing_task_control_bot/
├── bot.py                — Asosiy bot
├── config.py             — Sozlamalar
├── handlers/             — Buyruqlar va callback lар
├── services/             — Reminder, grafik, statistika
├── database/             — SQLite schema
├── assets/               — PNG shablon
└── generated_reports/    — Yaratilgan hisobotlar
```

### Systemd

```
service: marketing-task-control-bot
bot:     @allmax_vazifalarbot
```

---

## 6. instagram_bitrix_dm_lead_bot

> Instagram Direct xabarlardan avtomatik CRM lead yaratish — Meta Webhook → Claude AI parser → Bitrix24 → Telegram.

### Nima qiladi

1. Instagram DM ni **Meta Webhook** orqali real vaqtda qabul qiladi
2. Webhook imzosini (`X-Hub-Signature-256`) tekshiradi
3. Mijoz xabaridan **Regex + Claude AI** orqali ism va telefon ajratadi
4. Kontakt topilmasa, Instagram DM da **shablon xabar** yuboradi:
   > "Murojatingiz qabul qilindi. Batafsil ma'lumot berishimiz uchun ism va raqamingizni yozib qoldiring."
5. **Bitrix24 CRM** ga lead yaratadi
6. **Bitrix24 Projects** ga task ochadi (group_id=15, responsible_id=63)
7. **Telegram guruhiga** HTML formatlangan xabar yuboradi
8. **Target/reklama** orqali kelgan leadlarni alohida belgilaydi
9. Dublikat tekshiruvi — bir mijoz ikki marta lead bo'lmaydi (SQLite)

### Qanday ishlaydi

```
Instagram DM → Meta Webhook (POST /webhook)
                      │
          X-Hub-Signature-256 tekshiruvi
                      │
          Conversation state (SQLite) — yangi yoki davom?
                      │
        Regex parser → Claude AI parser (fallback)
                      │
             ┌────────┴────────┐
         Topildi           Topilmadi
             │                  │
    Bitrix CRM lead       Instagram DM da
    Bitrix Project task    shablon xabar
    Telegram xabar
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `fastapi` | Webhook server (`POST /webhook`, `GET /webhook` verify) |
| `uvicorn` | ASGI server |
| `anthropic` | Claude AI — kontakt parsing (fallback) |
| `httpx` | Meta Graph API + Bitrix24 API so'rovlari |
| `aiosqlite` | Conversation state, dublikat DB |
| `python-dotenv` | .env konfiguratsiya |

### Konfiguratsiya (.env)

```env
# Meta / Instagram
META_VERIFY_TOKEN=...
META_APP_SECRET=...
META_API_MODE=instagram_login        # yoki facebook_page
META_IG_USER_ACCESS_TOKEN=...
META_IG_BUSINESS_ID=...

# AI
ANTHROPIC_API_KEY=...

# Bitrix24
BITRIX_WEBHOOK_URL=https://allmax.bitrix24.kz/rest/.../
BITRIX_ASSIGNED_BY_ID=63
BITRIX_PROJECT_GROUP_ID=15
BITRIX_PROJECT_RESPONSIBLE_ID=63

# Telegram
LEAD_TELEGRAM_BOT_TOKEN=...
LEAD_TELEGRAM_CHAT_ID=-100...
```

### Fayllar

```
instagram_bitrix_dm_lead_bot/
├── run.py              — Ishga tushirish
├── app/
│   ├── main.py         — FastAPI endpointlar
│   ├── parser.py       — Regex + Claude AI parser
│   ├── bitrix.py       — Bitrix24 CRM + Projects
│   ├── instagram.py    — Meta Graph API DM yuborish
│   ├── telegram.py     — Telegram guruh xabar
│   ├── database.py     — Conversation state, dublikat
│   └── config.py       — .env sozlamalar
└── tests/
```

### Systemd

```
service: instagram-dm-lead-bot
port:    8002
webhook: https://allmax.tizm.uz/instagram/webhook
```

---

## 7. telegram_ai_assistant

> Claude AI bilan boshqariladigan **shaxsiy** Telegram akkaunt assistenti — erkin tilda topshiriq berish, AI bajaradi.

### Nima qiladi

- Telegram Bot (`@Claude_ai_oBot`) orqali erkin tilda topshiriq (TZ) berish
- Claude AI tool-use orqali **shaxsiy akkaunt** (`@Anvar_Abdurahmon`) nomidan ishlaydi
- Barcha chatlar, guruhlar, kanallardan xabar o'qiydi va yuboradi
- Ovoz xabarlarni matnga aylantiradi (faster-whisper)
- Suhbat tarixi saqlanadi (oxirgi 20 ta almashuv, JSON fayl)
- Faqat egasi (`OWNER_USER_ID`) foydalana oladi
- `receive_updates=False` — fon update'lardan keladigan xatolardan himoyalangan

**Misol topshiriqlar:**
- "ALLMAX SMM guruhidagi bu oy xabarlarimni yig'ib oylik hisobot qilib ber"
- "Bekaga 'holat qanday?' deb xabar yubor"
- "Saved Messages dagi so'nggi 10 ta xabarni ko'rsat"

### Claude AI toollar

| Tool | Vazifasi |
|---|---|
| `list_dialogs` | Barcha chatlar ro'yxati (guruhlar, kanallar, DM) |
| `get_chat_history` | Chat xabarlar tarixi (sana oralig'i bilan) |
| `search_messages` | Kalit so'z bo'yicha barcha chatlarda qidirish |
| `send_message` | Istalgan chatga xabar yuborish |
| `get_chat_info` | Chat haqida batafsil ma'lumot |
| `get_current_datetime` | Hozirgi sana va vaqtni olish |

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Buyruqlar boti (`@Claude_ai_oBot`) |
| `telethon` | Shaxsiy Telegram user-account client (`receive_updates=False`) |
| `anthropic` | Claude AI `claude-opus-4-8` tool-use agent |
| `faster-whisper` | Ovoz transkriptsiya |
| `python-dotenv` | .env konfiguratsiya |

### Konfiguratsiya (.env)

```env
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_PHONE=+998...
COMMAND_BOT_TOKEN=...        # @Claude_ai_oBot tokeni
OWNER_USER_ID=...            # Faqat shu user foydalana oladi
ANTHROPIC_API_KEY=...
```

### Fayllar

```
telegram_ai_assistant/
├── bot.py                — Aiogram bot (buyruqlar qabul)
├── claude_agent.py       — Claude AI agent (system prompt, tool loop)
├── telegram_client.py    — Telethon tools (list_dialogs, send_message...)
├── media_transcriber.py  — Ovoz transkriptsiya
├── memory_store.py       — Suhbat tarixi (JSON)
├── config.py             — .env sozlamalar
└── login_session.py      — Bir martalik session yaratish
```

### Systemd

```
service:      telegram-ai-assistant
bot:          @Claude_ai_oBot
user-session: @Anvar_Abdurahmon
```

---

## 8. allmax_ai_assistant

> Claude AI bilan boshqariladigan **ALLMAX kompaniya** Telegram akkaunt assistenti — `@allmaxshaxsiy` nomidan ishlaydi.

### Nima qiladi

- Telegram Bot (`@allmax_claude_aiBot`) orqali erkin tilda topshiriq berish
- Claude AI tool-use orqali **ALLMAX akkaunt** (`@allmaxshaxsiy`) nomidan ishlaydi
- Barcha kompaniya chatlar, guruhlar, kanallardan xabar o'qiydi va yuboradi
- Hisobot yig'ish, qidirish, statistika hisoblash
- Suhbat tarixi saqlanadi (oxirgi 20 ta almashuv)
- Faqat **admin** (ID: 6586004680) foydalana oladi

### Claude AI toollar

| Tool | Vazifasi |
|---|---|
| `list_dialogs` | Barcha ALLMAX chatlar ro'yxati |
| `get_chat_history` | Chat tarixi (sana oralig'i) |
| `search_messages` | Barcha chatlarda kalit so'z qidirish |
| `send_message` | ALLMAX akkauntidan xabar yuborish |
| `get_chat_info` | Chat haqida ma'lumot |
| `get_current_datetime` | Hozirgi sana va vaqt |

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Buyruqlar boti (`@allmax_claude_aiBot`) |
| `telethon` | ALLMAX Telegram user-account client (`allmax_cm_session`) |
| `anthropic` | Claude AI `claude-opus-4-8` tool-use agent |
| `faster-whisper` | Ovoz transkriptsiya |

### Konfiguratsiya (.env)

```env
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_PHONE=+998903935030
COMMAND_BOT_TOKEN=...        # @allmax_claude_aiBot tokeni
OWNER_USER_ID=6586004680
ANTHROPIC_API_KEY=...
```

### Fayllar

```
allmax_ai_assistant/
├── bot.py                — Aiogram bot
├── claude_agent.py       — Claude AI agent
├── telegram_client.py    — Telethon tools
├── media_transcriber.py  — Ovoz transkriptsiya
├── memory_store.py       — Suhbat tarixi (JSON)
└── config.py             — .env sozlamalar
```

### Systemd

```
service:      allmax-ai-assistant
bot:          @allmax_claude_aiBot
user-session: @allmaxshaxsiy (allmax_cm_session)
admin:        6586004680
```

---

## Infratuzilma

### Server holati

| Servis | Status | Port | Bot / Session | RAM |
|---|---|---|---|---|
| `allmax-telethon` | ✅ active | — | @allmaxshaxsiy | ~310 MB |
| `allmax-hr-bot` | ✅ active | — | @allmax_jbot | ~170 MB |
| `feedback-bot` | ✅ active | — | @allmax_feedback_bot | ~130 MB |
| `bitrix-lead-alert-bot` | ✅ active | 8000 | — | ~70 MB |
| `marketing-task-control-bot` | ✅ active | — | @allmax_vazifalarbot | ~115 MB |
| `instagram-dm-lead-bot` | ✅ active | 8002 | — | ~80 MB |
| `telegram-ai-assistant` | ✅ active | — | @Claude_ai_oBot | ~860 MB |
| `allmax-ai-assistant` | ✅ active | — | @allmax_claude_aiBot | ~220 MB |

Hammasi `systemctl enable`, `Restart=always` — server reboot bo'lsa avtomatik qayta ishga tushadi.

### Nginx (allmax.tizm.uz)

| URL | Port | Loyiha |
|---|---|---|
| `/instagram/webhook` | 8002 | instagram_bitrix_dm_lead_bot |
| `/tirox/webhook` | 8002 | instagram_bitrix_dm_lead_bot (TIROX kanal) |

### Utility skriptlar

| Fayl | Tavsif |
|---|---|
| `delete_tirox_leads.py` | Bitrix24 da TIROX integrasiya orqali tushgan leadlarni topib o'chiradi |
| `deploy.sh` | Server deploy skripti |

### Loglarni ko'rish

```bash
# Real vaqtda log kuzatish
journalctl -u allmax-telethon -f
journalctl -u allmax-hr-bot -f
journalctl -u instagram-dm-lead-bot -f

# Oxirgi 50 qator
journalctl -u allmax-telethon -n 50 --no-pager
```

### Git workflow

```bash
cd /opt/AllmaxProjects
git add -A
git commit -m "o'zgarish tavsifi"
git push origin master
```

### Barcha servislarni qayta ishga tushirish

```bash
systemctl restart allmax-telethon allmax-hr-bot feedback-bot bitrix-lead-alert-bot marketing-task-control-bot instagram-dm-lead-bot telegram-ai-assistant allmax-ai-assistant
```

---

*ALLMAX — Avtomatlashtirish va raqamli transformatsiya*
