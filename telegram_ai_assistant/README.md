# Telegram AI Assistant

Shaxsiy Telegram akkountingizni AI (Claude) yordamida boshqaruvchi universal assistant.
Bot orqali erkin tilda topshiriq (TZ) berasiz — masalan:

> "ALLMAX SMM guruhidagi oy davomida topshirgan hisobotlarimni yig'ib bitta qilib oylik hisobot qilib ber"

Claude kerakli guruhni topib, xabarlar tarixini o'qib, natijani sizga qaytaradi (yoki so'ralgan
chatga yuboradi).

## 1. O'rnatish

```bash
cd ~/telegram_ai_assistant
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 2. .env to'ldirish

| O'zgaruvchi | Qayerdan olinadi |
|---|---|
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | https://my.telegram.org → "API development tools" |
| `TELEGRAM_PHONE` | Sizning Telegram'ga ulangan telefon raqamingiz (+998...) |
| `COMMAND_BOT_TOKEN` | @BotFather → `/newbot` orqali yaratilgan bot tokeni |
| `OWNER_USER_ID` | @userinfobot ga yozib, o'z ID'ingizni oling |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com |

## 3. Shaxsiy akkountga kirish (bir martalik)

```bash
python login_session.py
```

Telefon raqamingizga kelgan kodni kiriting (va agar 2FA yoqilgan bo'lsa — parolingizni).
Muvaffaqiyatli bo'lsa, `user_session.session` fayli yaratiladi.

## 4. Ishga tushirish

```bash
python bot.py
```

Endi @BotFather orqali yaratgan botingizga yozing:

- `/start` — tanishtirish
- `/dialogs` — barcha chatlar ro'yxati (test uchun)
- Istalgan erkin matn — bu sizning TZ'ingiz, AI uni bajarib natija qaytaradi

## Xavfsizlik

- Bot faqat `OWNER_USER_ID` dan kelgan xabarlarga javob beradi.
- `user_session.session` fayli akkountingizga to'liq kirish huquqi beradi — uni hech kimga
  bermang va git'ga commit qilmang.
- Assistant sizning nomingizdan xabar o'qiy va yubora oladi — topshiriqlarni ehtiyotkorlik
  bilan beirng.

## Doimiy ishlashi uchun (ixtiyoriy)

Agar noutbuk yoqilgan paytda doimiy ishlashini xohlasangiz, `systemd` user service yoki
`tmux`/`screen` sessiyasida `python bot.py` ni ishga tushirib qoldirish mumkin.
