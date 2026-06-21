# Food Control Bot — Marketing Bo'limi Ovqat Nazorati

Marketing bo'limidagi 13 nafar xodim uchun ovqat buyurtma va hisobot boti.

---

## O'rnatish

```bash
cd food_control_bot
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

---

## .env sozlash

`.env.example` faylini `.env` nomi bilan ko'chiring va to'ldiring:

```bash
cp .env.example .env
```

```env
BOT_TOKEN=your_bot_token_here      # @BotFather dan olingan token
SUPER_ADMIN_ID=123456789           # Admin Telegram ID (raqam)
TIMEZONE=Asia/Tashkent
DB_PATH=food_control.db
ANCHOR_DATE=2026-06-21             # Siklning boshlanish sanasi
ANCHOR_WEEK=1                      # 1 yoki 2
ANCHOR_DAY=Yakshanba               # Hafta kuni nomi
ANCHOR_INDEX=6                     # 0-13 oralig'idagi indeks
```

### Bot token olish

1. Telegram da `@BotFather` ga yozing
2. `/newbot` buyrug'ini bering
3. Bot nomi va username kiriting
4. Olingan tokenni `BOT_TOKEN` ga joylashtiring

### Admin ID topish

`@userinfobot` ga `/start` yozing — u sizning Telegram ID ingizni ko'rsatadi.

---

## Botni ishga tushirish

```bash
source venv/bin/activate
python main.py
```

---

## Admin qanday sozlaydi

### 1-qadam: Botni ishga tushirish

`/start` bosing. Bot xodimlar ID so'raydi.

### 2-qadam: Xodimlar ID qo'shish

12 ta xodimning Telegram ID sini alohida qatorlarda yuboring:

```
123456789
987654321
111222333
...
```

Bot admin ID sini ham avtomatik qo'shadi → jami 13 ta ishtirokchi.

> **Muhim:** Har bir xodim botga `/start` bosishi kerak, aks holda bot ularga 13:30 da xabar yubora olmaydi.

### 3-qadam: Guruh ID qo'shish

Hisobot guruhining ID sini yuboring. Guruh ID ni topish uchun:
1. Botni guruhga qo'shing
2. Guruhga `@userinfobot` ni qo'shing yoki `/id` buyrug'i bering

### Keyinchalik sozlamalarni o'zgartirish

```
/set_users  — xodimlar ro'yxatini yangilash (12 ta ID qaytadan yuboriladi)
/set_group  — hisobot guruhini o'zgartirish
/set_menu   — menyuni tahrirlash
/set_cycle  — siklni boshqatan sozlash
```

---

## Menyu qanday yoziladi

`/set_menu` buyrug'i bilan yangi menyu yuboriladi:

```
1-HAFTA
Dushanba: 1-ovqat nomi | 2-ovqat nomi
Seshanba: 1-ovqat nomi | 2-ovqat nomi
Chorshanba: 1-ovqat nomi | 2-ovqat nomi
Payshanba: 1-ovqat nomi | 2-ovqat nomi
Juma: 1-ovqat nomi | 2-ovqat nomi
Shanba: 1-ovqat nomi | 2-ovqat nomi
Yakshanba: 1-ovqat nomi | 2-ovqat nomi

2-HAFTA
Dushanba: 1-ovqat nomi | 2-ovqat nomi
...
```

`|` belgisi 1-ovqat va 2-ovqatni ajratadi.

---

## Sikl qanday ishlaydi

Bot 14 kunlik (2 haftalik) siklda ishlaydi:

| Indeks | Hafta | Kun        |
|--------|-------|------------|
| 0      | 1     | Dushanba   |
| 1      | 1     | Seshanba   |
| ...    | ...   | ...        |
| 6      | 1     | Yakshanba  |
| 7      | 2     | Dushanba   |
| ...    | ...   | ...        |
| 13     | 2     | Yakshanba  |

**Formula:**
```
days_diff = (target_date - anchor_date).days
cycle_index = (anchor_index + days_diff) % 14
```

**Siklni o'zgartirish:**
```
/set_cycle 2026-06-21 1 Yakshanba
```

---

## 13:30 va 22:00 logikasi

### 13:30 — Ertangi taomnoma

- Bot ertangi kun menyusini hisoblab topadi
- Botga `/start` bosgan barcha 13 ta xodimga inline keyboard bilan yuboradi
- Hali `/start` bosmagan xodimlar haqida adminga xabar yuboradi

### 22:00 — Yakuniy hisobot

- Bugungi ovqat bo'yicha to'liq statistika
- Buyurtma berganlar, yeb tugatganlar, video yubormaganlar
- Adminga va guruhga yuboriladi

---

## Admin buyruqlari to'liq ro'yxati

| Buyruq       | Tavsif                              |
|--------------|-------------------------------------|
| `/start`     | Botni ishga tushirish / sozlash     |
| `/set_users` | Xodimlar ro'yxatini yangilash       |
| `/set_group` | Hisobot guruh ID sini o'zgartirish  |
| `/set_menu`  | Menyuni tahrirlash                  |
| `/set_cycle` | Sikl sozlamasini o'zgartirish       |
| `/report`    | Ertangi buyurtmalar hisoboti        |
| `/today`     | Bugungi menyu                       |
| `/tomorrow`  | Ertangi menyu                       |
| `/reset_day` | Bugungi buyurtmalarni tozalash      |
