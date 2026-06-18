# ALLMAX Projects

**ALLMAX** kompaniyasining barcha avtomatlashtirish loyihalari — Telegram botlar, Instagram integratsiya, CRM va AI yordamchilar.

**Server:** DigitalOcean VPS — Ubuntu 24.04 — `209.38.239.245` — 2 vCPU / 4 GB RAM (s-2vcpu-4gb)  
**AI:** Anthropic Claude `claude-opus-4-8` (barcha loyihalarda)  
**GitHub:** [alishex/projects](https://github.com/alishex/projects)

---

## Loyihalar royxati

| # | Loyiha | Tavsif | Port |
|---|---|---|---|
| 1 | [allmax_telethon](#1-allmax_telethon) | Telegram DM Community Agent — Claude AI auto-reply + lead | — |
| 2 | [allmax_hr_bot](#2-allmax_hr_bot) | HR onboarding va intervyu boti | — |
| 3 | [feedback_bot](#3-feedback_bot) | Mijoz fikr-mulohaza boti | — |
| 4 | [bitrix_lead_alert_bot](#4-bitrix_lead_alert_bot) | Bitrix24 yangi lead alert boti | 8000 |
| 5 | [marketing_task_control_bot](#5-marketing_task_control_bot) | Marketing jamoasi vazifalar boti | — |
| 6 | [instagram_bitrix_dm_lead_bot](#6-instagram_bitrix_dm_lead_bot) | Instagram DM lead boti | 8002 |
| 7 | [telegram_ai_assistant](#7-telegram_ai_assistant) | Claude AI shaxsiy Telegram assistenti | — |
| 8 | [allmax_ai_assistant](#8-allmax_ai_assistant) | Claude AI ALLMAX akkaunt assistenti | — |

---

## 1. allmax_telethon

> ALLMAX Telegram DM Community Agent — Claude AI yordamida mijozlar bilan suhbat, buyurtma yigish va Bitrix24 integratsiya

### Nima qiladi

**Community Agent (asosiy rejim):**
1. Telegram DM ga kelgan **matn, ovoz, video, rasm** xabarlarni o'qiydi
2. Claude AI oxirgi **30 kunlik to'liq suhbat tarixini** tahlil qilib javob beradi
3. Standart savollarga (manzil, narx, o'lcham, yetkazib berish, **ish vaqti 24/7**) avtomatik javob beradi
4. **MoySklad** dan real vaqtda mahsulot mavjudligi va narxini tekshiradi (`check_stock` tool)
5. Buyurtma ma'lumotlarini tabiiy suhbat orqali yig'adi (9 ta maydon)
6. Buyurtma to'liq bo'lganda **Bitrix24 CRM lead + Projects task** yaratadi
7. **Operator guruhiga** buyurtma xulasasi + Telegram havolasi yuboradi
8. Murakkab savollarda operatorga yo'naltiradi
9. Mijoz qaysi tilda yozsa — **shu tilda** javob beradi (O'zbek / Rus / Ingliz)

**Fallback rejim (Community Agent o'chirilganda):**
- Mijozdan ism va telefon so'raydi
- Bitrix24 ga lead yaratadi

### Buyurtma yig'ish (9 maydon)

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
| 9 | pochta | BTS / EMU / UzPost |

### Qanday ishlaydi

```
Yangi DM (matn/ovoz/video/rasm)
        |
  Burst collector (1.8s)
        |
  build_chat_history()
    - 30 kun matn tarixi
    - 48 soat ovoz/video transkriptsiya (faster-whisper)
    - so'nggi 3 ta rasm (Claude Vision)
        |
  CommunityAgent.process() — Claude API (agentic loop, max 4 iter)
    - check_stock tool     → moysklad.py → stok + narx → tool_result
    - order_complete tool  → Bitrix CRM + task + guruh xabar
    - needs_human tool     → operatorga yo'naltirish
    - oddiy javob          → mijozga yuboriladi (uz/ru/en)
```

### Do'kon ma'lumotlari (agent biladi)

| | |
|---|---|
| **Manzil** | Toshkent, Bunyodkor Savdo Majmuasi (Korzinka 1-qavat), metro: Mirzo Ulug'bek |
| **Telefon** | +998 78 555 31 31 |
| **Do'kon ish vaqti** | **24/7** — hech qachon yopilmaydi |
| **Call centre / Community** | Har kuni **09:00–22:00** |
| **Narx bosqichlari** | 99 000 / 149 900 / 199 900 / 249 900 / 299 900 / Premium |
| **To'lov** | Naqd, plastik, Uzum nasiya |
| **Yetkazib berish (viloyatlar)** | BTS (Nukus, Urganch, Buxoro, Navoiy, Samarqand, Qarshi, Termiz, Farg'ona, Namangan, Andijon, Guliston, Jizzax), EMU, UzPost |
| **Yetkazib berish (Toshkent)** | YandexGo kuryer |

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `telethon` | Telegram user-account client (`allmax_cm_session`) |
| `anthropic` | Claude AI — Community Agent (tool-use, agentic loop) |
| `faster-whisper` | Ovoz/video transkriptsiya (base model) |
| `requests` | Bitrix24 API + MoySklad API so'rovlari |
| `sqlite3` | Analytics + media transcription cache |
| `python-dotenv` | .env konfiguratsiya |

### Konfiguratsiya (.env)

```env
COMMUNITY_AGENT_ENABLE=true
COMMUNITY_ADDRESS=Toshkent sh., Bunyodkor Savdo Majmuasi ...
COMMUNITY_PHONE=+998 78 555 31 31
COMMUNITY_WORK_START=9
COMMUNITY_WORK_END=22
COMMUNITY_HISTORY_LIMIT=60
COMMUNITY_HISTORY_DAYS=30
COMMUNITY_MEDIA_HOURS=48
MOYSKLAD_TOKEN=<MoySklad Bearer token>
```

### Fayllar

| Fayl | Vazifasi |
|---|---|
| `main_ready_project.pyw` | Asosiy bot, event handler, Bitrix integratsiya |
| `community_agent.py` | Claude AI Community Agent (tool-use, agentic loop, ko'p til) |
| `moysklad.py` | MoySklad REST API — mahsulot qidirish + stok tekshiruvi |
| `media_handler.py` | Ovoz/video transkriptsiya, rasm encoding, SQLite cache |

### Systemd

```
service: allmax-telethon
user-session: @allmaxshaxsiy (allmax_cm_session)
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
- Barcha chatlar, guruhlar, kanallardan xabar o'qiydi va yuboradi
- **Ovoz xabarlarni** matnga aylantiradi (faster-whisper)
- **Suhbat tarixi** saqlanadi (oxirgi 20 ta almashuv)
- `receive_updates=False` — fon update'lardan keladigan TL xatolardan himoyalangan

### Claude AI toollar

| Tool | Vazifasi |
|---|---|
| `list_dialogs` | Barcha chatlar ro'yxati |
| `get_chat_history` | Chat xabarlar tarixi |
| `search_messages` | Kalit so'z bo'yicha qidirish |
| `send_message` | Xabar yuborish |
| `get_chat_info` | Chat haqida ma'lumot |

### Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram 3.x` | Buyruqlar boti |
| `telethon` | Telegram user-account client (`receive_updates=False`) |
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
- Barcha chatlar, guruhlar, kanallardan xabar o'qiydi va yuboradi
- Hisobot yig'ish, qidirish, statistika hisoblash
- **Suhbat tarixi** saqlanadi (oxirgi 20 ta almashuv)
- Faqat **admin** (ID: 6586004680) foydalana oladi

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

| Servis | Status | Port | Bot / Session |
|---|---|---|---|
| `allmax-telethon` | active | — | @allmaxshaxsiy |
| `allmax-hr-bot` | active | — | @allmax_jbot |
| `feedback-bot` | active | — | @allmax_feedback_bot |
| `bitrix-lead-alert-bot` | active | 8000 | — |
| `marketing-task-control-bot` | active | — | @allmax_vazifalarbot |
| `instagram-dm-lead-bot` | active | 8002 | — |
| `telegram-ai-assistant` | active | — | @Claude_ai_oBot |
| `allmax-ai-assistant` | active | — | @allmax_claude_aiBot |

Hammasi `systemctl enable`, `Restart=always` — server reboot bo'lsa avtomatik qayta ishga tushadi.

### Nginx (allmax.tizm.uz)

| URL | Port | Loyiha |
|---|---|---|
| `/instagram/` | 8002 | instagram_bitrix_dm_lead_bot |
| `/tirox/` | 8002 | instagram_bitrix_dm_lead_bot |

### Loglarni ko'rish

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
