# ALLMAX Projects

**ALLMAX** kompaniyasining barcha avtomatlashtirish loyihalari — Telegram botlar, Instagram integratsiya, CRM va AI yordamchilar.

**Server:** DigitalOcean VPS — Ubuntu 24.04 — `209.38.239.245`  
**AI:** Anthropic Claude `claude-opus-4-8` (barcha loyihalarda)  
**GitHub:** [alishex/projects](https://github.com/alishex/projects)

---

## Loyihalar ro'yxati

| # | Loyiha | Tavsif | Port |
|---|---|---|---|
| 1 | [allmax_telethon](#1-allmax_telethon) | Telegram DM lead capture boti | — |
| 2 | [allmax_hr_bot](#2-allmax_hr_bot) | HR onboarding va intervyu boti | — |
| 3 | [feedback_bot](#3-feedback_bot) | Mijoz fikr-mulohaza boti | — |
| 4 | [bitrix_lead_alert_bot](#4-bitrix_lead_alert_bot) | Bitrix24 yangi lead alert boti | 8000 |
| 5 | [marketing_task_control_bot](#5-marketing_task_control_bot) | Marketing jamoasi vazifalar boti | — |
| 6 | [instagram_bitrix_dm_lead_bot](#6-instagram_bitrix_dm_lead_bot) | Instagram DM lead boti | 8002 |
| 7 | [telegram_ai_assistant](#7-telegram_ai_assistant) | Claude AI shaxsiy Telegram assistenti | — |

---

## 1. allmax_telethon

> Telegram shaxsiy akkauntga kelgan DM xabarlardan avtomatik lead yaratadi

### Nima qiladi
1. Telegram DM ga yangi xabar kelganda mijozdan **ism va telefon** so'raydi
2. Matndan kontaktni **Regex + Claude AI** yordamida ajratib oladi
3. **Bitrix24 CRM** ga yangi lead yaratadi (dublikat tekshiruvi bilan)
4. **Bitrix24 Projects** ga avtomatik task ochadi (lead ga bog'liq)
5. **Telegram guruhiga** lead ma'lumotini yuboradi

### Qanday ishlaydi

```
Yangi DM → Burst collector (1.8s) → Contact parser → Shablon yuborish
                                              ↓ (ism+telefon topilsa)
                                    Bitrix CRM lead + Projects task + Guruh xabar
```

- **Burst protection:** 1.8 soniya oynada kelgan 5 tagacha xabarni birlashtiradi
- **Per-user queue:** Har foydalanuvchi uchun alohida asyncio worker
- **FloodWait handler:** Telegram limit berilsa kutadi
- **Dublikat himoya:** Bir telefon raqami uchun ikkinchi lead ochmaydi

### Fayl strukturasi

```
allmax_telethon/
└── main_ready_project.pyw   # Asosiy fayl (barcha logika shu yerda)
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `telethon` | Telegram user-account client |
| `anthropic` | Claude AI — kontakt parsing |
| `requests` | Bitrix24 API so'rovlari |
| `python-dotenv` | .env konfiguratsiya |

### Asosiy sozlamalar (.env)

```env
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
PHONE_NUMBER=+998...
SESSION_NAME=allmax_cm_session
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-opus-4-8
LEAD_GROUP=-100...              # Lead xabarlari yuboriladigan guruh
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

> Yangi xodimlarni onboarding qilish, intervyu o'tkazish va reglamentlarni boshqarish

### Nima qiladi
- Yangi xodimga **reglament va materiallar** yuboradi
- Avtomatik **intervyu savollari** beradi, javoblarni Claude AI bilan baholaydi
- Admin panel orqali **vakansiya, dars, material** boshqaradi
- **Rezyumeni** Claude AI tahlil qiladi va ball beradi
- **Clockster** davomat tizimi bilan integratsiya
- Har kuni belgilangan vaqtda **avtomatik bildirishnomalar** yuboradi

### Qanday ishlaydi

```
Foydalanuvchi /start → Ro'yxatdan o'tish → Intervyu bosqichlari
                                                    ↓
                              Claude AI javoblarni baholaydi (0-100 ball)
                                                    ↓
                              Admin natijani ko'radi → Onboarding tasdiqlash
```

### Fayl strukturasi

```
allmax_hr_bot/
├── main.py                        # Entry point
├── app/
│   ├── bot.py                     # Bot yaratish va dispatcher
│   ├── config.py                  # Konfiguratsiya (.env)
│   ├── database.py                # SQLite ulanish
│   ├── states.py                  # FSM holatlari
│   ├── handlers/
│   │   ├── start.py               # /start handler
│   │   ├── interview.py           # Intervyu oqimi
│   │   ├── onboarding.py          # Onboarding bosqichlari
│   │   ├── resume.py              # Rezyume qabul qilish
│   │   ├── vacancies.py           # Vakansiyalar
│   │   ├── admin.py               # Admin panel
│   │   ├── dynamic_admin.py       # Dinamik admin funksiyalar
│   │   └── followup.py            # Kuzatuv xabarlari
│   ├── keyboards/
│   │   ├── user_keyboards.py      # Foydalanuvchi tugmalari
│   │   ├── admin_keyboards.py     # Admin tugmalari
│   │   └── dynamic_admin_keyboards.py
│   ├── services/
│   │   ├── openai_service.py      # Claude AI integratsiya
│   │   ├── scoring_service.py     # Intervyu balllash
│   │   ├── scheduler_service.py   # APScheduler vazifalar
│   │   ├── clockster_service.py   # Davomat tizimi
│   │   ├── docx_reader.py         # Word fayl o'qish
│   │   ├── pdf_service.py         # PDF fayl o'qish
│   │   ├── excel_service.py       # Excel hisobotlar
│   │   ├── lesson_service.py      # Darslar boshqaruvi
│   │   ├── material_service.py    # Materiallar boshqaruvi
│   │   └── dynamic_service.py     # Dinamik kontent
│   └── utils/
│       ├── logger.py              # Logging
│       ├── texts.py               # Matnlar
│       └── validators.py          # Tekshiruvlar
├── reglamentlar/                  # Reglament .docx fayllar (14 ta)
├── tests/
│   ├── smoke_test.py
│   └── openai_parameter_guard_test.py
└── requirements.txt
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Telegram Bot API |
| `anthropic` | Claude AI — baholash va tahlil |
| `aiosqlite` | Async SQLite |
| `apscheduler` | Avtomatik vazifalar |
| `python-docx` | Word fayllarni o'qish |
| `openpyxl` | Excel hisobotlar |

### Systemd

```
service: allmax-hr-bot
bot: @allmax_jbot
```

---

## 3. feedback_bot

> Mijozlardan baho va fikr-mulohaza yig'ish boti

### Nima qiladi
- Mijoz **1 dan 5 gacha baho** beradi (yulduzchalar bilan)
- Matn, rasm, video, ovoz xabar qabul qiladi
- Xabarlarni **paket** shaklida to'plab adminga yuboradi
- **JSON faylda** saqlaydi (atomic write, race condition himoyasi)
- Eski xabarlarni avtomatik o'chiradi

### Qanday ishlaydi

```
/start → Asosiy menyu → Fikr qoldirish tugmasi
                               ↓
                    Reyting tanlash (⭐ 1-5)
                               ↓
                    Matn/Media qabul qilish
                               ↓
              Admin guruhiga paket yuborish + JSON saqlash
```

### Fayl strukturasi

```
feedback_bot/
├── bot.py                    # Entry point, polling
├── config.py                 # Token va sozlamalar
├── states.py                 # FSM holatlari
├── handlers/
│   ├── start.py              # /start va asosiy menyu
│   └── feedback.py           # Feedback oqimi (lock + atomic write)
├── keyboards/
│   ├── menu.py               # Asosiy menyu
│   └── rating.py             # Yulduzcha tugmalar
└── storage/
    └── feedbacks.json        # Saqlangan feedbacklar
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Telegram Bot API |
| `aiofiles` | Async fayl o'qish/yozish |

### Muhim texnik detallar
- `asyncio.Lock` — bir vaqtda bir nechtasi JSON yozsa conflict bo'lmasin
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
- FastAPI webhook server orqali ishlaydi

### Qanday ishlaydi

```
APScheduler (har 60s) → Bitrix24 API so'rov (crm.item.list)
                                ↓
                    Yangi lead ID lar checkpoint bilan taqqoslanadi
                                ↓
                    Yangi leadlar → Telegram guruhiga xabar
                                ↓
                    Checkpoint yangilanadi (SQLite)
```

### Fayl strukturasi

```
bitrix_lead_alert_bot/
├── run.py                    # Entry point (uvicorn)
├── app/
│   ├── main.py               # FastAPI app
│   ├── config.py             # Konfiguratsiya
│   ├── database.py           # SQLite (checkpoint saqlash)
│   ├── scheduler.py          # APScheduler — polling loop
│   ├── processor.py          # Lead qayta ishlash logikasi
│   ├── bitrix.py             # Bitrix24 API wrapper
│   ├── telegram_client.py    # Telegram xabar yuborish
│   ├── lead_utils.py         # Lead formatlash
│   └── logger.py             # Logging
└── scripts/
    └── get_chat_id.py        # Chat ID topish yordamchi skript
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `fastapi` | Web server |
| `uvicorn` | ASGI server |
| `apscheduler` | Har daqiqa polling |
| `aiosqlite` | Checkpoint saqlash |
| `httpx` | Bitrix24 API so'rovlari |

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
- **9 ta marketing xodim** uchun sozlangan
- Prioritet tizimi: Yuqori / O'rta / Past

### Qanday ishlaydi

```
Admin → Vazifa yaratish → Xodim tayinlash → Deadline belgilash
                                                    ↓
                              APScheduler (har daqiqa deadline tekshiradi)
                                                    ↓
                                    Deadline yaqinlashsa eslatma
                                                    ↓
                              Xodim "Bajarildi" bosadi → Hisobot
```

### Fayl strukturasi

```
marketing_task_control_bot/
├── bot.py                         # Entry point
├── config.py                      # Konfiguratsiya
├── database/
│   ├── database.py                # SQLite ulanish
│   ├── models.py                  # Jadval modellari
│   └── repositories.py           # DB so'rovlari
├── handlers/
│   ├── admin.py                   # Admin panel
│   ├── employee.py                # Xodim interfeysi
│   ├── task_creation.py           # Vazifa yaratish oqimi
│   ├── task_management.py         # Vazifa boshqarish
│   ├── graph_reports.py           # Grafik hisobotlar
│   ├── settings.py                # Sozlamalar
│   └── common.py                  # Umumiy handlerlar
├── keyboards/
│   ├── admin_keyboards.py
│   ├── employee_keyboards.py
│   └── inline_keyboards.py
├── services/
│   ├── task_service.py            # Vazifa biznes logikasi
│   ├── reminder_service.py        # Eslatma yuborish
│   ├── notification_service.py    # Bildirishnomalar
│   ├── priority_service.py        # Prioritet hisoblash
│   ├── matrix_image_service.py    # PNG hisobot generatsiya
│   └── cleanup_service.py         # Eski ma'lumotlarni tozalash
├── middlewares/
│   └── auth_middleware.py         # Foydalanuvchi ruxsati
├── states/
│   └── task_states.py             # FSM holatlari
├── utils/
│   ├── constants.py
│   ├── datetime_utils.py
│   ├── text_utils.py
│   └── logger.py
├── assets/
│   └── toliq_ish_vazifalar_template.png
└── tests/
    ├── test_matrix_image_service.py
    └── test_priority_service.py
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
5. **Bitrix24 Projects** ga task ochadi (CRM ga bog'liq)
6. **Telegram guruhiga** HTML formatlangan xabar yuboradi
7. **Target/reklama** orqali kelgan leadlarni alohida belgilaydi

### Qanday ishlaydi

```
Instagram DM → Meta Webhook (POST /webhook)
                      ↓
            Signature tekshiruvi (X-Hub-Signature-256)
                      ↓
            Conversation sync worker (har 45s)
                      ↓
        Regex parser → Claude AI parser (fallback)
                      ↓
    Dublikat tekshiruvi (3 qatlam: DB + Bitrix + SQLite)
                      ↓
    Bitrix CRM lead + Projects task + Telegram xabar
```

### Dublikat himoya (3 qatlam)
1. `processed_events` — bir xil webhook event qayta ishlanmaydi
2. `sent_leads` + `conversations` — bir telefon bir martadan lead
3. Bitrix24 `crm.duplicate.findbycomm` — CRM da ham tekshiriladi

### Target reklama aniqlash
Payload ichidan `referral`, `ad_id`, `ad_title` yoki kalit so'zlar (`target`, `reklama`, `ads`) topilsa:
- Lead alohida Bitrix24 stage ga tushadi
- Telegram xabarida 🎯 belgisi qo'shiladi

### Fayl strukturasi

```
instagram_bitrix_dm_lead_bot/
├── run.py                              # Entry point (uvicorn)
├── app/
│   ├── main.py                         # FastAPI app, startup/shutdown
│   ├── config.py                       # Settings dataclass (.env)
│   ├── database.py                     # SQLite init va migration
│   ├── models.py                       # Pydantic modellari
│   ├── logger.py                       # Logging sozlash
│   ├── routes/
│   │   └── webhook.py                  # GET/POST /webhook endpointlari
│   ├── services/
│   │   ├── instagram_service.py        # Instagram DM yuborish
│   │   ├── bitrix_service.py           # Bitrix24 CRM + Projects
│   │   ├── telegram_service.py         # Telegram lead xabarlari
│   │   ├── duplicate_service.py        # Dublikat tekshiruvi
│   │   ├── target_detector.py          # Reklama/target aniqlash
│   │   ├── meta_signature.py           # Webhook imzo tekshiruvi
│   │   └── openai_parser.py            # Claude AI kontakt parser
│   ├── workers/
│   │   └── conversation_sync.py        # Background sync worker
│   └── utils/
│       ├── phone.py                    # Telefon normalizatsiya
│       ├── text.py                     # Matn tozalash
│       ├── time_utils.py               # Vaqt formatlash
│       └── retry.py                    # HTTP retry logika
├── tests/
│   ├── test_contact_parser.py
│   ├── test_duplicate.py
│   ├── test_phone.py
│   └── test_target_detector.py
├── Dockerfile
├── docker-compose.yml
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
| `pydantic` | Ma'lumot modellari |

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
  - Barcha chatlar va guruhlar ro'yxatini ko'radi
  - Istalgan chatning xabarlar tarixini o'qiydi
  - Xabar qidiradi
  - Xabar yuboradi
  - Chat ma'lumotlarini oladi
- **Ovoz xabarlarni** matnга aylantiradi (`faster-whisper`)
- **Suhbat tarixi** saqlanadi (oxirgi 20 ta almashuv)

### Qanday ishlaydi

```
Bot foydalanuvchisi → @Claude_ai_oBot ga xabar yozadi
                                ↓
                    Claude AI (claude-sonnet-4-6)
                    tool-use agentic loop (max 25 qadam)
                                ↓
            list_dialogs / get_chat_history / search_messages
            send_message / get_chat_info
                                ↓
                    Telethon — real Telegram akkaunt orqali bajaradi
                                ↓
                    Natija → foydalanuvchiga javob
```

### Fayl strukturasi

```
telegram_ai_assistant/
├── bot.py                  # Entry point — aiogram bot (OWNER ga restricted)
├── claude_agent.py         # Anthropic tool-use agentic loop
├── telegram_client.py      # TelegramToolset: 5 ta tool
├── config.py               # .env konfiguratsiya
├── memory_store.py         # Suhbat tarixi (conversation_history.json)
├── media_transcriber.py    # Ovoz → matn (faster-whisper)
└── login_session.py        # Bir martalik session yaratish
```

### Claude AI toollar

| Tool | Vazifasi |
|---|---|
| `list_dialogs` | Barcha chatlar ro'yxati (limit bilan) |
| `get_chat_history` | Chat xabarlar tarixi |
| `search_messages` | Kalit so'z bo'yicha qidirish |
| `send_message` | Xabar yuborish |
| `get_chat_info` | Chat haqida ma'lumot |

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Buyruqlar boti |
| `telethon` | Telegram user-account client |
| `anthropic` | Claude AI tool-use agent |
| `faster-whisper` | Ovoz transkriptsiya |

### Systemd

```
service: telegram-ai-assistant
bot: @Claude_ai_oBot
user-session: @Anvar_Abdurahmon
```

---

## Infratuzilma

### Server holati

| Servis | Status | Port | Texnologiya |
|---|---|---|---|
| `allmax-telethon` | ✅ active | — | Telethon + Claude |
| `allmax-hr-bot` | ✅ active | — | aiogram + Claude |
| `feedback-bot` | ✅ active | — | aiogram |
| `bitrix-lead-alert-bot` | ✅ active | 8000 | FastAPI + APScheduler |
| `marketing-task-control-bot` | ✅ active | — | aiogram + APScheduler |
| `instagram-dm-lead-bot` | ✅ active | 8002 | FastAPI + Claude |
| `telegram-ai-assistant` | ✅ active | — | aiogram + Telethon + Claude |

Hammasi `systemctl enable`, `Restart=always` — server reboot bo'lsa avtomatik qayta ishga tushadi.

### Deploy qilish

```bash
# Fayllarni serverga yuborish
rsync -avz \
  --exclude venv --exclude __pycache__ --exclude .env \
  --exclude "*.session" --exclude "*.db" --exclude "*.sqlite3" \
  ./loyiha_nomi/ root@209.38.239.245:/opt/AllmaxProjects/loyiha_nomi/

# Paketlarni o'rnatish
ssh root@209.38.239.245 "
  cd /opt/AllmaxProjects/loyiha_nomi
  venv/bin/pip install -r requirements.txt
  systemctl restart <service-name>
"

# Loglarni ko'rish
journalctl -u <service-name> -f
```

### Git workflow

```bash
# Serverda
cd /opt/AllmaxProjects
git add -A
git commit -m "o'zgarish tavsifi"
git push origin master
```

---

## .gitignore (umumiy)

Quyidagi fayllar **hech qachon** commitlanmaydi:

```
.env          # API kalitlar va tokenlar
*.session     # Telegram session fayllar
*.db / *.sqlite3  # Ma'lumotlar bazasi
venv/ / .venv/    # Virtual muhit
__pycache__/      # Python cache
*.log             # Log fayllar
```

---

*ALLMAX — Avtomatlashtirish va raqamli transformatsiya*
