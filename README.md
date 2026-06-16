# AllmaxProjects

**ALLMAX** kompaniyasining barcha avtomatlashtirish va bot loyihalari to'plami.

---

## Loyihalar

### 1. `allmax_telethon` — Telegram DM Lead Bot
Telegram shaxsiy akkaunt orqali kelgan xabarlarni kuzatadi va avtomatik CRM ga yuboradi.

- Telethon (user-account) asosida ishlaydi
- Yangi DM kelganda mijozdan ism va telefon so'raydi
- Kontaktni regex + Claude AI yordamida aniqlaydi
- **Bitrix24 CRM** ga yangi lead yaratadi (dublikat tekshiruvi bilan)
- **Bitrix24 Projects** ga avtomatik task ochadi
- Lead ma'lumotini Telegram guruhiga yuboradi
- Burst protection va FloodWait handler mavjud

**Stack:** Python, Telethon, Anthropic Claude, Bitrix24 API

---

### 2. `allmax_hr_bot` — HR va Onboarding Boti
Yangi xodimlarni onboarding qilish, intervyu o'tkazish va reglamentlarni tarqatish uchun Telegram bot.

- Yangi xodimga reglament va materiallar yuboradi
- Intervyu savollarini avtomatik beradi va javoblarni baholaydi
- Admin panel orqali xodimlarni boshqarish
- Claude AI yordamida rezyume va javoblarni tahlil qiladi
- Clockster integratsiya (davomat tizimi)

**Stack:** Python, aiogram 3.x, Anthropic Claude, SQLite, APScheduler

---

### 3. `feedback_bot` — Mijoz Fikr-Mulohaza Boti
Mijozlardan baho va fikr-mulohaza yig'ish uchun Telegram bot.

- Mijoz 1-5 baho beradi
- Matn, rasm, video, ovoz xabarlarini qabul qiladi
- Paket tarzida saqlaydi va adminga yuboradi
- Atomic JSON saqlash (race condition himoyasi)

**Stack:** Python, aiogram 3.x

---

### 4. `bitrix_lead_alert_bot` — Bitrix24 Lead Alert Boti
Bitrix24 CRM ga yangi lead tushganda Telegram guruhiga darhol xabar yuboradi.

- Har daqiqada Bitrix24 ni tekshiradi (polling)
- Yangi lead aniqlanganda formatlangan xabar yuboradi
- Checkpoint tizimi — bir lead ikki marta yuborilmaydi
- SQLite orqali yuborilgan leadlarni saqlaydi
- FastAPI webhook server

**Stack:** Python, FastAPI, APScheduler, SQLite, Bitrix24 API

---

### 5. `marketing_task_control_bot` — Marketing Vazifalar Boti
Marketing jamoasi uchun vazifalar berish, nazorat qilish va hisobot olish tizimi.

- Admin vazifa yaratadi va xodimlarga tayinlaydi
- Deadline eslatmalari avtomatik yuboriladi
- Xodim bajarilgan vazifani belgilaydi
- Grafik hisobotlar (PNG matritsa)
- 9 ta marketing xodim uchun sozlangan

**Stack:** Python, aiogram 3.x, SQLite, APScheduler, Pillow

---

### 6. `instagram_group_format_bot` — Instagram Lead Formatlash Boti
Instagram DM orqali kelgan murojaatlarni Telegram guruhiga formatlangan holda yuboradi.

- Meta/Instagram Webhook API orqali xabarlarni qabul qiladi
- Claude AI yordamida kontakt ma'lumotlarini ajratib oladi
- Bitrix24 CRM ga lead yaratadi
- Formatlangan xabarni Telegram guruhiga yuboradi

**Stack:** Python, FastAPI, Anthropic Claude, Meta Webhook API, Bitrix24 API

---

## Infratuzilma

| Servis | Holat | Port |
|---|---|---|
| `allmax-telethon` | systemd, Restart=always | — |
| `allmax-hr-bot` | systemd, Restart=always | — |
| `feedback-bot` | systemd, Restart=always | — |
| `bitrix-lead-alert-bot` | systemd, Restart=always | 8000 |
| `marketing-task-control-bot` | systemd, Restart=always | — |
| `instagram-group-format-bot` | systemd, Restart=always | 8001 |

**Server:** DigitalOcean VPS, Ubuntu 24.04  
**AI:** Anthropic Claude (`claude-opus-4-8`) — barcha loyihalarda OpenAI o'rniga ishlatiladi

---

## Deploy

```bash
# Loyihani serverga yuklash
rsync -avz --exclude venv --exclude __pycache__ --exclude .env \
  ./loyiha_nomi/ root@SERVER_IP:/opt/AllmaxProjects/loyiha_nomi/

# Servisni qayta ishga tushirish
systemctl restart <service-name>

# Loglarni ko'rish
journalctl -u <service-name> -f
```

---

*ALLMAX — Avtomatlashtirish va raqamli transformatsiya*
