# ALLMAX Feedback Bot

Marketing bo'limi uchun Telegram bot — xodimlar va mijozlardan reyting va fikr-mulohaza yig'adi, natijani admin guruhiga yuboradi.

---

## Papka tuzilmasi

```
bot.py                    # Entrypoint — polling ishga tushiradi
config.py                 # BOT_TOKEN va ADMIN_CHAT_ID (.env dan)
states.py                 # FSM holatlari (FeedbackStates)
handlers/
  start.py                # /start buyrug'i va /chatid yordamchisi
  feedback.py             # To'liq feedback jarayoni (reyting → izoh → rasm/video → telefon)
keyboards/
  menu.py                 # Asosiy menyu
  rating.py               # 1–5 yulduz reyting va telefon so'rash klaviaturalari
storage/
  feedbacks.json          # Barcha feedbacklar JSON shaklda (atomik yozuv)
```

---

## Imkoniyatlar

- **Yulduz reytingi** — 1 dan 5 gacha inline tugmalar orqali baho berish
- **Matnli izoh** — ixtiyoriy sharh yozish imkoniyati
- **Rasm/video yuklash** — albom ko'rinishida bir nechta media qabul qiladi
- **Telefon raqam** — ixtiyoriy telefon raqam so'rash
- **Admin guruhiga yuborish** — to'liq feedback yig'ilgach admin guruhiga yuboriladi
- **JSON saqlash** — `storage/feedbacks.json` da barcha feedbacklar saqlanadi (oxirgi 50 matn, 10 media)

---

## Texnologiyalar

| Kutubxona | Maqsad |
|-----------|--------|
| `aiogram 3.7` | Telegram Bot API (FSM, Router) |
| `python-dotenv` | .env sozlamalari |

---

## O'rnatish

```bash
cd /opt/AllmaxProjects/feedback_bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## .env sozlash

```env
BOT_TOKEN=...           # @BotFather dan olingan bot token
ADMIN_CHAT_ID=-100...   # Feedbacklar yuboriladigan guruh yoki kanal ID
```

---

## Ishga tushirish

```bash
source venv/bin/activate
python bot.py
```

---

## systemd (server)

```
/etc/systemd/system/feedback-bot.service
```

```bash
systemctl status feedback-bot
journalctl -u feedback-bot -f
systemctl restart feedback-bot
```

---

## Feedback jarayoni

```
/start
  → "Fikr bildirish" tugmasi
    → Reyting (1–5 yulduz)
      → Matnli izoh (ixtiyoriy, o'tkazish tugmasi bor)
        → Rasm/video (ixtiyoriy, o'tkazish tugmasi bor)
          → Telefon raqam (ixtiyoriy, o'tkazish tugmasi bor)
            → Admin guruhiga yuborish ✓
```

---

## Muhim eslatmalar

- `storage/feedbacks.json` git da saqlanmaydi — DB backup tashqi tizimda qilinsin
- `ADMIN_CHAT_ID` guruh bo'lsa, bot o'sha guruhga admin huquqlari bilan qo'shilgan bo'lishi kerak
