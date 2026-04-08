# Expense Bot Project

Telegram bot bitta foydalanuvchi uchun pul nazorat qilishga mo‘ljallangan.

## Imkoniyatlar
- Kirim qo‘shish
- Chiqim qo‘shish
- To‘lov turi: Naqd / Karta
- Valyuta: So‘m / Dollar / Yevro
- Joriy balansni valyuta va hisob bo‘yicha ko‘rish
- Bugungi va oylik hisobot
- Oxirgi yozuvlar
- CSV eksport
- Oxirgi yozuvni o‘chirish

## O‘rnatish
1. Python 3.11 yoki undan yuqori versiya o‘rnating.
2. `.env.example` faylini `.env` deb nusxalang.
3. `.env` ichiga `BOT_TOKEN` va `OWNER_TELEGRAM_ID` ni yozing.
4. Kutubxonalarni o‘rnating:
   ```bash
   pip install -r requirements.txt
   ```
5. Botni ishga tushiring:
   ```bash
   python bot.py
   ```

## Eslatma
- Har bir valyuta alohida hisoblanadi.
- So‘m, Dollar va Yevro bir-biriga qo‘shib yuborilmaydi.
- Eski bazada yangi ustunlar bo‘lmasa, bot ularni avtomatik qo‘shadi.
