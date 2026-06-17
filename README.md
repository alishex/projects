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
| 8 | [allmax_ai_assistant](#8-allmax_ai_assistant) | Claude AI ALLMAX akkaunt assistenti | — |

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

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `telethon` | Telegram user-account client |
| `anthropic` | Claude AI — kontakt parsing |
| `requests` | Bitrix24 API sorovlari |
| `sqlite3` | Analytics logging |
| `python-dotenv` | .env konfiguratsiya |

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

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Telegram Bot API |
| `anthropic` | Claude AI — baholash va tahlil |
| `aiosqlite` | Async SQLite |
| `apscheduler` | Avtomatik vazifalar |

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

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Telegram Bot API |

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

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `fastapi` | Web server |
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

### Qanday ishlaydi

```
Instagram DM -> Meta Webhook (POST /webhook)
                      |
            Signature tekshiruvi (X-Hub-Signature-256)
                      |
        Regex parser -> Claude AI parser (fallback)
                      |
    Bitrix CRM lead + Projects task + Telegram xabar
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `fastapi` | Webhook server |
| `anthropic` | Claude AI — kontakt parsing |
| `httpx` | Meta Graph API, Bitrix24 |
| `aiosqlite` | Conversation state, dublikat DB |

### Systemd

```
service: instagram-dm-lead-bot
port: 8002
webhook: https://allmax.tizm.uz/instagram/webhook
```

---

## 7. telegram_ai_assistant

> Claude AI bilan boshqariladigan shaxsiy Telegram akkaunt assistenti

### Nima qiladi
- Telegram Bot (`@Claude_ai_oBot`) orqali **erkin tilda** topshiriq berish
- Claude AI **tool-use** orqali real Telegram akkaunt nomidan harakatlar bajaradi
- Barcha chatlar, guruhlar, kanallardan xabar oqiydi va yuboradi
- **Ovoz xabarlarni** matnga aylantiradi (faster-whisper)
- **Suhbat tarixi** saqlanadi (oxirgi 20 ta almashuv)

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

### Systemd

```
service: telegram-ai-assistant
bot: @Claude_ai_oBot
user-session: @Anvar_Abdurahmon
```

---

## 8. allmax_ai_assistant

> Claude AI bilan boshqariladigan ALLMAX kompaniya Telegram akkaunt assistenti

### Nima qiladi
- Telegram Bot (`@allmax_claude_aiBot`) orqali **erkin tilda** topshiriq berish
- Claude AI **tool-use** orqali **ALLMAX akkaunt** (`@allmaxshaxsiy`) nomidan ishlaydi
- Barcha chatlar, guruhlar, kanallardan xabar oqiydi va yuboradi
- Hisobot yigish, qidirish, statistika hisoblash
- **Suhbat tarixi** saqlanadi (oxirgi 20 ta almashuv)
- Faqat **admin** (ID: 6586004680) foydalana oladi

### Qanday ishlaydi

```
Admin -> @allmax_claude_aiBot ga xabar yozadi
                    |
        Claude AI (claude-opus-4-8) tool-use
                    |
    list_dialogs / get_chat_history / search_messages
    send_message / get_chat_info
                    |
    Telethon — @allmaxshaxsiy akkaunt orqali bajaradi
                    |
    Natija -> adminga javob
```

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Buyruqlar boti |
| `telethon` | Telegram user-account client (allmax_cm_session) |
| `anthropic` | Claude AI tool-use agent |
| `faster-whisper` | Ovoz transkriptsiya |

### Systemd

```
service: allmax-ai-assistant
bot: @allmax_claude_aiBot
user-session: @allmaxshaxsiy (allmax_cm_session)
admin: 6586004680
```

---

## Infratuzilma

### Server holati

| Servis | Status | Port | Bot |
|---|---|---|---|
| `allmax-telethon` | active | — | — |
| `allmax-hr-bot` | active | — | @allmax_jbot |
| `feedback-bot` | active | — | @allmax_feedback_bot |
| `bitrix-lead-alert-bot` | active | 8000 | — |
| `marketing-task-control-bot` | active | — | @allmax_vazifalarbot |
| `instagram-dm-lead-bot` | active | 8002 | — |
| `telegram-ai-assistant` | active | — | @Claude_ai_oBot |
| `allmax-ai-assistant` | active | — | @allmax_claude_aiBot |

Hammasi `systemctl enable`, `Restart=always` — server reboot bolsa avtomatik qayta ishga tushadi.

### Nginx (allmax.tizm.uz)

| URL | Port | Loyiha |
|---|---|---|
| `/instagram/` | 8002 | instagram_bitrix_dm_lead_bot |
| `/tirox/` | 8002 | instagram_bitrix_dm_lead_bot |

### Loglarni korish

```bash
journalctl -u <service-name> -f
```

### Git workflow

```bash
cd /opt/AllmaxProjects
git add -A
git commit -m ozgarish tavsifi
git push origin master
```

---

*ALLMAX — Avtomatlashtirish va raqamli transformatsiya*
