# ALLMAX Projects

**ALLMAX** kompaniyasining barcha avtomatlashtirish loyihalari — Telegram botlar, Instagram integratsiya, CRM va AI yordamchilar.

**Server:** DigitalOcean VPS — Ubuntu 24.04 — `209.38.239.245`  
**AI:** Anthropic Claude `claude-opus-4-8` (barcha loyihalarda)  
**GitHub:** [alishex/projects](https://github.com/alishex/projects)

---

## Loyihalar royxati

| # | Loyiha | Tavsif | Port |
|---|---|---|---|
| 1 | [allmax_telethon](#1-allmax_telethon) | Telegram DM lead capture boti | — |
| 2 | [allmax_hr_bot](#2-allmax_hr_bot) | HR onboarding va intervyu boti | — |
| 3 | [feedback_bot](#3-feedback_bot) | Mijoz fikr-mulohaza boti | — |
| 4 | [bitrix_lead_alert_bot](#4-bitrix_lead_alert_bot) | Bitrix24 yangi lead alert boti | 8000 |
| 5 | [marketing_task_control_bot](#5-marketing_task_control_bot) | Marketing jamoasi vazifalar boti | — |
| 6 | [instagram_bitrix_dm_lead_bot](#6-instagram_bitrix_dm_lead_bot) | Instagram DM lead boti | 8002 |
| 7 | [telegram_ai_assistant](#7-telegram_ai_assistant) | Claude AI shaxsiy Telegram assistenti | — |
| 8 | [analytics_report_bot](#8-analytics_report_bot) | Soatlik Telegram+Instagram statistika boti | — |

---

## 1. allmax_telethon

> Telegram shaxsiy akkauntga kelgan DM xabarlardan avtomatik lead yaratadi

### Nima qiladi
1. Telegram DM ga yangi xabar kelganda mijozdan **ism va telefon** soradi
2. Matndan kontaktni **Regex + Claude AI** yordamida ajratib oladi
3. **Bitrix24 CRM** ga yangi lead yaratadi (dublikat tekshiruvi bilan)
4. **Bitrix24 Projects** ga avtomatik task ochadi (lead ga bogliq)
5. **Telegram guruhiga** lead malumotini yuboradi
6. Har bir DM ni **SQLite** ga yozadi (analytics uchun)

### Qanday ishlaydi

```
Yangi DM -> Burst collector (1.8s) -> Contact parser -> Shablon yuborish
                                              |
                                   (ism+telefon topilsa)
                                    Bitrix CRM lead + Projects task + Guruh xabar
                                              |
                                    SQLite analytics log (dm_events)
```

- **Burst protection:** 1.8 soniya oynada kelgan 5 tagacha xabarni birlashtiradi
- **Per-user queue:** Har foydalanuvchi uchun alohida asyncio worker
- **FloodWait handler:** Telegram limit berilsa kutadi
- **Dublikat himoya:** Bir telefon raqami uchun ikkinchi lead ochmaydi
- **Analytics:** `dm_events` jadvalida user_id va timestamp saqlanadi

### Fayl strukturasi

```
allmax_telethon/
├── main_ready_project.pyw
└── analytics/
    └── telegram_dm_log.sqlite3
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `telethon` | Telegram user-account client |
| `anthropic` | Claude AI — kontakt parsing |
| `requests` | Bitrix24 API sorovlari |
| `sqlite3` | Analytics logging |
| `python-dotenv` | .env konfiguratsiya |

### Asosiy sozlamalar (.env)

```env
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
PHONE_NUMBER=+998...
SESSION_NAME=allmax_cm_session
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-opus-4-8
LEAD_GROUP=-100...
BITRIX_ENABLE=true
BITRIX_WEBHOOK_URL=https://...
BITRIX_PROJECT_ENABLE=true
BITRIX_PROJECT_GROUP_ID=15
BITRIX_PROJECT_BIND_TO_CRM=true
```

### Systemd

```
service: allmax-telethon
```

---

## 2. allmax_hr_bot

> Yangi xodimlarni onboarding qilish, intervyu otkazish va reglamentlarni boshqarish

### Nima qiladi
- Yangi xodimga **reglament va materiallar** yuboradi
- Avtomatik **intervyu savollari** beradi, javoblarni Claude AI bilan baholaydi
- Admin panel orqali **vakansiya, dars, material** boshqaradi
- **Rezyumeni** Claude AI tahlil qiladi va ball beradi
- **Clockster** davomat tizimi bilan integratsiya
- Har kuni belgilangan vaqtda **avtomatik bildirishnomalar** yuboradi

### Qanday ishlaydi

```
Foydalanuvchi /start -> Royxatdan otish -> Intervyu bosqichlari
                                                    |
                              Claude AI javoblarni baholaydi (0-100 ball)
                                                    |
                              Admin natijani koradi -> Onboarding tasdiqlash
```

### Fayl strukturasi

```
allmax_hr_bot/
├── main.py
├── app/
│   ├── bot.py
│   ├── config.py
│   ├── database.py
│   ├── states.py
│   ├── handlers/
│   │   ├── start.py
│   │   ├── interview.py
│   │   ├── onboarding.py
│   │   ├── resume.py
│   │   ├── vacancies.py
│   │   ├── admin.py
│   │   ├── dynamic_admin.py
│   │   └── followup.py
│   ├── keyboards/
│   ├── services/
│   │   ├── openai_service.py
│   │   ├── scoring_service.py
│   │   ├── scheduler_service.py
│   │   ├── clockster_service.py
│   │   ├── docx_reader.py
│   │   ├── pdf_service.py
│   │   ├── excel_service.py
│   │   └── lesson_service.py
│   └── utils/
├── reglamentlar/
└── requirements.txt
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Telegram Bot API |
| `anthropic` | Claude AI — baholash va tahlil |
| `aiosqlite` | Async SQLite |
| `apscheduler` | Avtomatik vazifalar |
| `python-docx` | Word fayllarni oqish |
| `openpyxl` | Excel hisobotlar |

### Systemd

```
service: allmax-hr-bot
bot: @allmax_jbot
```

---

## 3. feedback_bot

> Mijozlardan baho va fikr-mulohaza yigish boti

### Nima qiladi
- Mijoz **1 dan 5 gacha baho** beradi
- Matn, rasm, video, ovoz xabar qabul qiladi
- Xabarlarni **paket** shaklida toplab adminga yuboradi
- **JSON faylda** saqlaydi (atomic write, race condition himoyasi)

### Qanday ishlaydi

```
/start -> Asosiy menyu -> Fikr qoldirish tugmasi
                               |
                    Reyting tanlash (1-5 yulduz)
                               |
                    Matn/Media qabul qilish
                               |
              Admin guruhiga paket yuborish + JSON saqlash
```

### Fayl strukturasi

```
feedback_bot/
├── bot.py
├── config.py
├── states.py
├── handlers/
│   ├── start.py
│   └── feedback.py
├── keyboards/
│   ├── menu.py
│   └── rating.py
└── storage/
    └── feedbacks.json
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Telegram Bot API |
| `aiofiles` | Async fayl oqish/yozish |

### Muhim texnik detallar
- `asyncio.Lock` — bir vaqtda bir nechtasi JSON yozsa conflict bolmasin
- `os.replace()` — atomic write (yarim yozilgan fayl qolmaydi)

### Systemd

```
service: feedback-bot
bot: @allmax_feedback_bot
```

---

## 4. bitrix_lead_alert_bot

> Bitrix24 CRM ga yangi lead tushganda Telegram guruhiga darhol xabar yuboradi

### Nima qiladi
- Har **1 daqiqada** Bitrix24 ni tekshiradi (polling)
- Yangi lead aniqlanganda **formatlangan xabar** yuboradi
- **Checkpoint tizimi** — bir lead ikki marta yuborilmaydi
- SQLite da yuborilgan leadlarni saqlaydi

### Qanday ishlaydi

```
APScheduler (har 60s) -> Bitrix24 API sorov (crm.item.list)
                                |
                    Yangi lead ID lar checkpoint bilan taqqoslanadi
                                |
                    Yangi leadlar -> Telegram guruhiga xabar
                                |
                    Checkpoint yangilanadi (SQLite)
```

### Fayl strukturasi

```
bitrix_lead_alert_bot/
├── run.py
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── scheduler.py
│   ├── processor.py
│   ├── bitrix.py
│   ├── telegram_client.py
│   ├── lead_utils.py
│   └── logger.py
└── scripts/
    └── get_chat_id.py
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `fastapi` | Web server |
| `uvicorn` | ASGI server |
| `apscheduler` | Har daqiqa polling |
| `aiosqlite` | Checkpoint saqlash |
| `httpx` | Bitrix24 API sorovlari |

### Systemd

```
service: bitrix-lead-alert-bot
port: 8000
```

---

## 5. marketing_task_control_bot

> Marketing jamoasi uchun vazifalar berish, nazorat qilish va hisobot tizimi

### Nima qiladi
- Admin **vazifa yaratadi** va xodimlarga tayinlaydi
- **Deadline eslatmalari** avtomatik yuboriladi
- Xodim **bajarilgan deb belgilaydi**
- **Grafik hisobotlar** (PNG matritsa shaklida) yuboradi
- Prioritet tizimi: Yuqori / Orta / Past

### Qanday ishlaydi

```
Admin -> Vazifa yaratish -> Xodim tayinlash -> Deadline belgilash
                                                    |
                              APScheduler (har daqiqa deadline tekshiradi)
                                                    |
                                    Deadline yaqinlashsa eslatma
                                                    |
                              Xodim "Bajarildi" bosadi -> Hisobot
```

### Fayl strukturasi

```
marketing_task_control_bot/
├── bot.py
├── config.py
├── database/
│   ├── database.py
│   ├── models.py
│   └── repositories.py
├── handlers/
│   ├── admin.py
│   ├── employee.py
│   ├── task_creation.py
│   ├── task_management.py
│   └── graph_reports.py
├── services/
│   ├── task_service.py
│   ├── reminder_service.py
│   ├── matrix_image_service.py
│   └── cleanup_service.py
└── utils/
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Telegram Bot API |
| `aiosqlite` | Vazifalar bazasi |
| `apscheduler` | Deadline tekshirish |
| `Pillow` | PNG hisobot generatsiya |

### Systemd

```
service: marketing-task-control-bot
bot: @allmax_vazifalarbot
```

---

## 6. instagram_bitrix_dm_lead_bot

> Instagram Direct xabarlardan avtomatik CRM lead yaratish va kuzatish tizimi

### Nima qiladi
1. Instagram DM Meta Webhook orqali **real vaqtda** qabul qiladi
2. Mijoz xabaridan **ism va telefon** ajratadi (Regex + Claude AI)
3. Kontakt topilmasa, Instagram DM da **shablon xabar** yuboradi
4. **Bitrix24 CRM** ga lead yaratadi
5. **Bitrix24 Projects** ga task ochadi
6. **Telegram guruhiga** HTML formatlangan xabar yuboradi
7. **Target/reklama** orqali kelgan leadlarni alohida belgilaydi
8. Barcha muloqotlarni **SQLite** da saqlaydi (analytics uchun)

### Qanday ishlaydi

```
Instagram DM -> Meta Webhook (POST /webhook)
                      |
            Signature tekshiruvi (X-Hub-Signature-256)
                      |
            Conversation sync worker (har 45s)
                      |
        Regex parser -> Claude AI parser (fallback)
                      |
    Dublikat tekshiruvi (3 qatlam: DB + Bitrix + SQLite)
                      |
    Bitrix CRM lead + Projects task + Telegram xabar
```

### Dublikat himoya (3 qatlam)
1. `processed_events` — bir xil webhook event qayta ishlanmaydi
2. `sent_leads` + `conversations` — bir telefon bir martadan lead
3. Bitrix24 `crm.duplicate.findbycomm` — CRM da ham tekshiriladi

### Fayl strukturasi

```
instagram_bitrix_dm_lead_bot/
├── run.py
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── routes/
│   │   └── webhook.py
│   ├── services/
│   │   ├── instagram_service.py
│   │   ├── bitrix_service.py
│   │   ├── telegram_service.py
│   │   ├── duplicate_service.py
│   │   ├── target_detector.py
│   │   ├── meta_signature.py
│   │   └── openai_parser.py
│   └── workers/
│       └── conversation_sync.py
├── data/
│   └── instagram_dm_bot.sqlite3
└── requirements.txt
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `fastapi` | Webhook server |
| `uvicorn` | ASGI server |
| `anthropic` | Claude AI — kontakt parsing |
| `httpx` | Meta Graph API, Bitrix24 |
| `aiosqlite` | Conversation state, dublikat DB |
| `pydantic` | Malumot modellari |

### Systemd

```
service: instagram-dm-lead-bot
port: 8002
```

---

## 7. telegram_ai_assistant

> Claude AI bilan boshqariladigan shaxsiy Telegram akkaunt assistenti

### Nima qiladi
- Telegram Bot (`@Claude_ai_oBot`) orqali **erkin tilda** topshiriq berish
- Claude AI **tool-use** orqali real Telegram akkaunt nomidan harakatlar bajaradi:
  - Barcha chatlar va guruhlar royxatini koradi
  - Istalgan chatning xabarlar tarixini oqiydi
  - Xabar qidiradi va yuboradi
  - Chat malumotlarini oladi
- **Ovoz xabarlarni** matnga aylantiradi (`faster-whisper` + `ffmpeg`)
- **Suhbat tarixi** saqlanadi (oxirgi 20 ta almashuv)

### Qanday ishlaydi

```
Bot foydalanuvchisi -> @Claude_ai_oBot ga xabar yozadi
                                |
                    Claude AI (claude-sonnet-4-6)
                    tool-use agentic loop (max 25 qadam)
                                |
            list_dialogs / get_chat_history / search_messages
            send_message / get_chat_info
                                |
                    Telethon — real Telegram akkaunt orqali bajaradi
                                |
                    Natija -> foydalanuvchiga javob
```

### Fayl strukturasi

```
telegram_ai_assistant/
├── bot.py
├── claude_agent.py
├── telegram_client.py
├── config.py
├── memory_store.py
├── media_transcriber.py
└── login_session.py
```

### Claude AI toollar

| Tool | Vazifasi |
|---|---|
| `list_dialogs` | Barcha chatlar royxati |
| `get_chat_history` | Chat xabarlar tarixi |
| `search_messages` | Kalit soz boyicha qidirish |
| `send_message` | Xabar yuborish |
| `get_chat_info` | Chat haqida malumot |

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Buyruqlar boti |
| `telethon` | Telegram user-account client |
| `anthropic` | Claude AI tool-use agent |
| `faster-whisper` | Ovoz transkriptsiya |
| `ffmpeg` | Audio konvertatsiya |

### Systemd

```
service: telegram-ai-assistant
bot: @Claude_ai_oBot
user-session: @Anvar_Abdurahmon
```

---

## 8. analytics_report_bot

> Telegram va Instagram murojaatlarini har soatda tahlil qilib chiroyli hisobot yuboradigan bot

### Nima qiladi
- Har soat **:00 da** (10:00, 11:00, 12:00 ...) avtomatik ishga tushadi
- **Telegram DM** statistikasini `allmax_telethon` analytics DB dan oladi
- **Instagram DM** statistikasini `instagram_bitrix_dm_lead_bot` DB dan oladi
- Claude AI yordamida **chiroyli hisobot** matni yaratadi (emoji, uzbek tili, # * - yoq)
- Belgilangan **Telegram guruhiga** hisobot yuboradi
- Barcha vaqtlar **UTC+5 (Toshkent)** vaqt zonasida

### Qanday ishlaydi

```
APScheduler (har soat :00)
        |
Telegram DB sorov (dm_events) + Instagram DB sorov (conversations)
        |
Claude AI -> Chiroyli hisobot matni
        |
Telegram guruhiga xabar yuborish
```

### Malumot manbalari

| Kanal | DB fayl | Jadval | Malumot |
|---|---|---|---|
| Telegram | `allmax_telethon/analytics/telegram_dm_log.sqlite3` | `dm_events` | unique_users, total_messages |
| Instagram | `instagram_bitrix_dm_lead_bot/data/instagram_dm_bot.sqlite3` | `conversations` | total, contacts, targets |

### Hisobot tarkibi
- Sana, kun nomi va soat oraligi (UTC+5)
- Telegram DM: yangi murojaat soni, jami xabarlar
- Instagram DM: suhbatlar, kontakt qoldirganlar, target reklama orqali kelganlar
- Jami murojaat va eng faol kanal
- Emoji bilan bezatilgan sof matn formatida

### Fayl strukturasi

```
analytics_report_bot/
├── bot.py
└── requirements.txt
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `anthropic` | Claude AI — hisobot matni generatsiya |
| `apscheduler` | Har soat :00 da cron task |
| `httpx` | Telegram Bot API sorovlari |
| `sqlite3` | Analytics DB dan malumot oqish |
| `python-dotenv` | .env konfiguratsiya |

### Asosiy sozlamalar (.env)

```env
BOT_TOKEN=...
CHAT_ID=-100...
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-opus-4-8
TIMEZONE_OFFSET=5
TELEGRAM_DB=/opt/AllmaxProjects/allmax_telethon/analytics/telegram_dm_log.sqlite3
INSTAGRAM_DB=/opt/AllmaxProjects/instagram_bitrix_dm_lead_bot/data/instagram_dm_bot.sqlite3
```

### Systemd

```
service: analytics-report-bot
```

---

## Infratuzilma

### Server holati

| Servis | Status | Port | Texnologiya |
|---|---|---|---|
| `allmax-telethon` | active | — | Telethon + Claude |
| `allmax-hr-bot` | active | — | aiogram + Claude |
| `feedback-bot` | active | — | aiogram |
| `bitrix-lead-alert-bot` | active | 8000 | FastAPI + APScheduler |
| `marketing-task-control-bot` | active | — | aiogram + APScheduler |
| `instagram-dm-lead-bot` | active | 8002 | FastAPI + Claude |
| `telegram-ai-assistant` | active | — | aiogram + Telethon + Claude |
| `analytics-report-bot` | active | — | APScheduler + Claude |

Hammasi `systemctl enable`, `Restart=always` — server reboot bolsa avtomatik qayta ishga tushadi.

### Deploy qilish

```bash
rsync -avz \
  --exclude venv --exclude __pycache__ --exclude .env \
  --exclude "*.session" --exclude "*.sqlite3" \
  ./loyiha_nomi/ root@209.38.239.245:/opt/AllmaxProjects/loyiha_nomi/

ssh root@209.38.239.245 "
  cd /opt/AllmaxProjects/loyiha_nomi
  venv/bin/pip install -r requirements.txt
  systemctl restart <service-name>
"
```

### Loglarni korish

```bash
journalctl -u <service-name> -f
```

### Git workflow

```bash
cd /opt/AllmaxProjects
git add -A
git commit -m "ozgarish tavsifi"
git push origin master
```

---

## .gitignore (umumiy)

```
.env
*.session
*.db / *.sqlite3
venv/ / .venv/
__pycache__/
*.log
```

---

*ALLMAX — Avtomatlashtirish va raqamli transformatsiya*
