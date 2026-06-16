# Marketing Task Control Bot

Marketing bo‘limi uchun Telegram bot: admin topshiriq beradi, xodim deadline taklif qiladi, admin tasdiqlaydi yoki tahrirlaydi, reminderlar ishlaydi va faol vazifalar original Eisenhower grafik shabloni ustiga yozilgan rasm ko‘rinishida yuboriladi.

## Muhim grafik qoidasi

Botdagi asosiy hisobot oddiy matnli post emas, grafik rasm hisoblanadi. Shablon loyiha ichida quyidagi manzilda saqlanadi:

```text
assets/toliq_ish_vazifalar_template.png
```

Taqdim etilgan ZIP ichida texnik topshiriqda ko‘rsatilgan `ali 2.png` nomli fayl mavjud bo‘lmadi; ZIP ichidagi yagona grafik fayl `To'liq ish vazifalar/Безымянный-1.jpg` edi. Shu yuklangan original rasm piksel ko‘rinishini saqlagan holda PNG formatiga o‘tkazilib, majburiy loyiha manziliga joylashtirildi.

Grafik servis har safar shablonning nusxasini oladi. Original faylga yozmaydi. Vazifa matnlari va deadline lar mavjud rangli kataklarning ustiga bevosita yoziladi; vazifalar orqasiga yangi rectangle, badge yoki fon blok chizilmaydi. Bitta katakda beshtadan ko‘p faol vazifa bo‘lsa, shu shablonda keyingi sahifa yaratiladi.

## Imkoniyatlar

- 1 admin va oldindan yaratiladigan 9 ta xodim lavozimi.
- Admin tomonidan Telegram user ID biriktirish va olib tashlash.
- FSM asosidagi topshiriq yaratish jarayoni.
- Xodim deadline taklifi va admin tasdig‘i/tahriri.
- `ACTIVE`, `OVERDUE`, `COMPLETED`, `CANCELLED` holatlari hamda tarix.
- 24 soat, 3 soat, 1 soat reminderlari va overdue ogohlantirishlari.
- Reminder takrorlanishini SQLite orqali bloklash.
- Xodim va admin uchun original shablondagi shaxsiy grafiklar.
- Faol topshiriqlarni priority/xodim/deadline bo‘yicha boshqarish.
- Tugatilgan topshiriqlar arxivi.
- Ruxsatsiz foydalanuvchilar uchun to‘liq bloklash.

## Talablar

- Python 3.11 yoki undan yuqori
- Linux/Kali Linux/Ubuntu VPS
- Telegram bot tokeni va admin Telegram user ID

Python versiyasini tekshiring:

```bash
python3 --version
```

## O‘rnatish

Arxivni oching va loyiha papkasiga kiring:

```bash
unzip marketing_task_control_bot_ready.zip
cd marketing_task_control_bot
```

Virtual environment yarating:

```bash
python3 -m venv venv
source venv/bin/activate
```

Kutubxonalarni o‘rnating:

```bash
pip install -r requirements.txt
```

`.env` fayl yarating:

```bash
cp .env.example .env
nano .env
```

`.env` ichiga haqiqiy qiymatlaringizni yozing:

```env
BOT_TOKEN=your_real_bot_token
ADMIN_ID=your_real_admin_telegram_id
TIMEZONE=Asia/Tashkent
DATABASE_PATH=data/database.sqlite3
LOG_LEVEL=INFO
```

## BotFather orqali token olish

1. Telegram ichida rasmiy `@BotFather` ni oching.
2. `/newbot` yuboring va bot nomi hamda username tanlang.
3. BotFather bergan tokenni `.env` faylidagi `BOT_TOKEN` qiymatiga yozing.
4. Tokenni boshqa odamga yubormang va kod ichiga yozmang.

## Telegram user ID ni aniqlash

Admin va har bir xodimning raqamli Telegram user ID si kerak bo‘ladi. ID ni ishonchli ID ko‘rsatuvchi bot orqali yoki mavjud tashkilot ichki usulingiz bilan aniqlang. Admin ID ni `.env` dagi `ADMIN_ID` ga yozing. Xodim ID larini botning `👥 Xodimlar` yoki `⚙️ Sozlamalar` menyusi orqali biriktiring.

## Botni ishga tushirish

```bash
python bot.py
```

Birinchi ishga tushishda `data/database.sqlite3` avtomatik yaratiladi va quyidagi 9 lavozim tayyor bo‘ladi:

1. SMM Manager
2. Brandface
3. Community Manager
4. Graphic Designer #1
5. Graphic Designer #2
6. Mobilograf #1
7. Mobilograf #2
8. Stories Maker
9. IT Systems Employee

## Birinchi topshiriq yaratish

1. Admin botda `/start` yuboradi.
2. `👥 Xodimlar` yoki `⚙️ Sozlamalar` bo‘limida xodim lavozimiga Telegram user ID biriktiradi.
3. `➕ Topshiriq berish` ni bosadi.
4. Xodim, to‘liq matn, grafik uchun qisqa nom va priority ni tanlaydi.
5. `✅ Yuborish` ni bosadi.
6. Xodim olingan topshiriqdagi `📅 Deadline taklif qilish` tugmasini bosib, `DD.MM.YYYY HH:MM` formatida muddat yuboradi.
7. Admin deadline ni ma’qullaydi yoki tahrirlaydi.
8. Deadline tasdiqlangach, xodimga va adminga grafik rasm yuboriladi.

## Grafikni ko‘rish

- Admin: `📊 Ish vazifalari grafigi` → xodimni tanlaydi.
- Xodim: `📊 Mening ish vazifalarim grafigi` yoki `🔄 Grafikni yangilash` ni bosadi.
- Grafikda faqat `ACTIVE` va `OVERDUE` topshiriqlar ko‘rinadi.
- Tugatilgan topshiriqlar faol grafikdan yo‘qoladi, bazada arxiv sifatida qoladi.

## Reminder va overdue jarayoni

Bot APScheduler yordamida deadline larni har daqiqada tekshiradi. 24 soat, 3 soat va 1 soat qolganda kerakli xabarlarni yuboradi. Deadline o‘tganda status `OVERDUE` bo‘ladi, grafikda `KECHIKKAN` yozuvi chiqadi. Yuborilgan reminderlar bazadagi `reminders` jadvalida saqlanadi va bot qayta ishga tushganidan keyin ham takroran yuborilmaydi.

## Testlarni ishga tushirish

```bash
pytest
```

Sintaksis tekshiruvi:

```bash
python -m compileall .
```

## Kali Linux yoki VPS da `screen` orqali doimiy ishlatish

```bash
screen -S marketing_task_bot
source venv/bin/activate
python bot.py
```

Screen oynasidan chiqish:

```text
Ctrl+A, keyin D
```

Qayta kirish:

```bash
screen -r marketing_task_bot
```

Botni qayta ishga tushirish kerak bo‘lsa, ishlayotgan jarayonni `Ctrl+C` bilan to‘xtating va yana:

```bash
python bot.py
```

## Baza backup qilish

Botni vaqtincha to‘xtatib, bazani nusxalang:

```bash
cp data/database.sqlite3 data/database_backup_$(date +%F_%H-%M).sqlite3
```

Backup faylini xavfsiz joyda saqlang. `.env` faylini ommaviy arxivga qo‘shmang.

## Log fayllari

Bot loglari terminalda va quyidagi faylda saqlanadi:

```text
logs/bot.log
```

Oxirgi yozuvlarni ko‘rish:

```bash
tail -f logs/bot.log
```

## Shriftlar

Grafikdagi o‘zbekcha harflar uchun servis tizimdagi `DejaVuSans` yoki `LiberationSans` shriftidan foydalanadi. Batafsil ma’lumot `assets/fonts/README.md` faylida mavjud. Loyiha mualliflik huquqi noma’lum shrift fayllarini tarqatmaydi.

## Xavfsizlik

- Begona Telegram user ID uchun bot faqat `Bu bot faqat egasi uchun ishlaydi.` javobini beradi.
- Admin tokeni faqat `.env` faylida saqlanadi.
- Barcha xabar va callback lar auth middleware orqali tekshiriladi.
- Xodim faqat o‘z vazifalari va o‘z grafigini ko‘radi.
