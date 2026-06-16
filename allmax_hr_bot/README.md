# ALLMAX Universal HR Bot Agent — Dinamik Admin Panel versiyasi

Ushbu loyiha ALLMAX uchun Telegram HR bot-agent bo‘lib, nomzod arizasi, AI intervyu, PDF/Excel eksport, intervyudan keyingi follow-up, 7 kunlik stajirovka, dars testlari, yakuniy test va Clockster nazoratini boshqaradi.

Ushbu versiyaning asosiy farqi: **vakansiyalar va reglamentlar endi Telegramdagi `/admin` panel orqali boshqariladi.** Yangi lavozim qo‘shish, reglamentni almashtirish yoki yangi dars/test tayyorlash uchun kodni o‘zgartirish va server papkasiga qo‘lda fayl tashlash talab qilinmaydi.

## Tuzatilgan xatolar

- Telegram `can't parse entities: Unsupported start tag "<"` xatosi bartaraf etildi. Admin/reglament matnidan keladigan `<`, `>`, `&` kabi belgilar HTML-safe ko‘rinishda yuboriladi.
- GPT reasoning modellarda `temperature=0.2` yuborilishi natijasida chiqadigan `400 Bad Request` xatosi bartaraf etilgan: GPT-5/o-model ishlatilsa `temperature` yuborilmaydi.
- Clockster nazorati faqat stajirovka va yakuniy test tugagandan keyin ishga tushadi.

## Texnologiyalar

- Python 3.10+
- aiogram 3.x
- SQLite
- OpenAI API, qat’iy JSON va fallback
- python-docx, pypdf, reportlab, openpyxl
- APScheduler, python-dotenv, logging

## O‘rnatish

```bash
cd allmax_hr_bot
python -m venv .venv
source .venv/bin/activate       # Linux / macOS
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` ichida kamida quyidagilarni yozing:

```env
BOT_TOKEN=TELEGRAM_BOT_TOKEN
OPENAI_API_KEY=OPENAI_API_KEY
OPENAI_MODEL=gpt-5.5
OPENAI_REASONING_EFFORT=high
ADMIN_IDS=123456789
TIMEZONE=Asia/Tashkent
```

Botni ishga tushirish:

```bash
python main.py
```

Birinchi ishga tushishda mavjud boshlang‘ich vakansiyalar va `reglamentlar/` papkasidagi dastlabki DOCX reglamentlar bazaga import qilinadi. Keyingi barcha o‘zgarishlar admin paneldan bajariladi.

## Admin panelga kirish

Telegramda `.env` dagi `ADMIN_IDS` foydalanuvchisidan yuboring:

```text
/admin
```

Admin bosh sahifasida odatiy HR bo‘limlari bilan birga yangi tugma bor:

```text
⚙️ Dinamik vakansiya va reglament boshqaruvi
```

U orqali quyidagi bo‘limlar ochiladi:

1. `📋 Vakansiyalarni boshqarish`
2. `📚 Reglamentlarni boshqarish`
3. `🔗 Vakansiya va reglament bog‘lash`
4. `🧠 AI materiallarni yaratish`
5. `📦 Reglament versiyalari`
6. `📊 Dars va test materiallari`
7. `📝 O‘zgarishlar tarixi`

Panel boshida reglamenti yoki tasdiqlangan dars materiali yetishmayotgan faol vakansiyalar bo‘yicha ogohlantirish ko‘rsatiladi.

## Yangi vakansiya qo‘shish

`/admin` → `⚙️ Dinamik...` → `📋 Vakansiyalarni boshqarish` → `➕ Yangi vakansiya qo‘shish`.

Bot ketma-ket so‘raydi:

1. O‘zbekcha nomi;
2. Ruscha nomi;
3. Qisqa tavsifi;
4. Asosiy vazifalari;
5. Asosiy talablari;
6. Ish grafigi;
7. Darhol faol qilish yoki yashirish.

`active` holatida saqlangan vakansiya foydalanuvchi bosadigan `💼 Bo‘sh ish o‘rinlari` menyusida avtomatik ko‘rinadi. `hidden`, `draft` va `archived` holatdagi vakansiyalar yangi ariza uchun ko‘rinmaydi.

### Vakansiyani tahrirlash va statuslar

Admin vakansiya nomi, tavsifi, vazifalari, talablari, ish grafigi, intervyu savollari soni, stajirovka kunlari, darslar soni va yakuniy test savollari sonini paneldan o‘zgartiradi.

Statuslar:

- `active` — userlarga chiqadi;
- `hidden` — bazada turadi, userga chiqmaydi;
- `draft` — tayyorlanayotgan vakansiya;
- `archived` — yangi ariza qabul qilinmaydi.

Arxivlash tasdiqlash bilan bajariladi.

## Yangi reglament yuklash

`/admin` → `📚 Reglamentlarni boshqarish` → `➕ Yangi reglament yuklash`.

Jarayon:

1. Reglament nomini yozing.
2. Tegishli vakansiyalarni belgilang; bir nechta vakansiya tanlash mumkin.
3. Reglament turini tanlang.
4. Telegram orqali `.docx`, `.pdf` yoki `.txt` fayl yuboring.
5. Bot faylni xavfsiz nom bilan `reglamentlar/uploads/` ichiga saqlaydi va matnni ajratadi.
6. Bot qisqa mazmun, fayl turi va versiyani ko‘rsatadi.
7. `✅ Faollashtirish` tugmasini bosing.

PDF rasm/screenshot shaklida bo‘lib, matn ajralmasa, bot DOCX yoki TXT formatida yuborishni so‘raydi.

## Reglamentni almashtirish va versiyaga qaytish

`🔄 Reglamentni yangilash` orqali mavjud reglamentni tanlang va yangi fayl yuboring. Eski fayl o‘chmaydi; yangi fayl `v2`, `v3` va hokazo ko‘rinishida saqlanadi.

- Yangi versiya tasdiqlangandan keyin yangi nomzodlar va yangi boshlanadigan stajirovkalar uchun ishlatiladi.
- Nomzod intervyuni yoki xodim stajirovkani boshlagan paytdagi reglament versiyalari `regulation_version_snapshot` maydonida qotirib saqlanadi.
- Keyin reglament o‘zgarsa ham boshlangan jarayon eski snapshot asosida davom etadi.

Oldingi versiyani faollashtirish:

`📦 Reglament versiyalari` yoki `↩️ Oldingi versiyaga qaytish` → reglament → kerakli `v1/v2/...` → tasdiqlash.

## Vakansiyaga reglament bog‘lash

`🔗 Vakansiya va reglament bog‘lash` bo‘limida:

1. Vakansiyani tanlang.
2. Faol reglamentni belgilang.
3. Reglament qayerda ishlatilishini tanlang:
   - hammasi uchun;
   - faqat intervyu uchun;
   - faqat darslar uchun;
   - faqat testlar uchun;
   - dars va test uchun.

Bir vakansiyaga bir nechta reglament bog‘lanishi mumkin. AI faqat bog‘langan va faol versiyalardagi matndan foydalanadi.

## AI intervyu, dars va test materiallarini yaratish

Reglament faollashtirilgandan keyin bot shu vakansiya uchun materiallarni yangilashni taklif qiladi. Shu amalni alohida `🧠 AI materiallarni yaratish` bo‘limidan ham boshlash mumkin.

Variantlar:

- `✅ Hammasini qayta yaratish` — intervyu shabloni, darslar va testlar;
- `🧠 Faqat intervyu`;
- `📘 Faqat darslar`;
- `📝 Faqat testlar`.

Yaratilgan materiallar avval `draft` holatida saqlanadi. Admin ko‘rib chiqqach `✅ Tasdiqlash va faollashtirish` tugmasini bosadi. Userlarga faqat `active` materiallar beriladi. Agar faol shablon hali bo‘lmasa, bot faol reglament snapshotidan xavfsiz fallback/AI orqali material hosil qiladi.

## Dars va testlarni tahrirlash

`📊 Dars va test materiallari` bo‘limidan vakansiyani tanlang.

- Darsni tanlab uning mazmunini tahrirlash mumkin.
- Test savolini tanlab savol, A/B/C/D variantlari, to‘g‘ri javob va izohni o‘zgartirish mumkin.
- Yangi yakuniy test savoli qo‘shish mumkin; u avval `draft` bo‘ladi.
- Keraksiz savolni arxivlash mumkin; arxivlangan savol userga yuborilmaydi.

Test savolini tahrirlash formati:

```text
Savol | A varianti | B varianti | C varianti | D varianti | A | Izoh
```

## O‘zgarishlar tarixi va xavfsizlik

Faqat `.env` dagi `ADMIN_IDS` foydalanuvchilari o‘zgarish kirita oladi. Quyidagi harakatlar `admin_change_logs` hamda `audit_logs` jadvallariga yoziladi:

- vakansiya yaratish/tahrirlash/status o‘zgarishi;
- reglament yaratish, versiya yuklash, faollashtirish yoki arxivlash;
- vakansiya-reglament bog‘lanishi;
- AI material yaratish va faollashtirish;
- dars yoki test savolini tahrirlash.

Tokenlar kod ichiga yozilmaydi. Telegram, OpenAI va Clockster tokenlarini faqat `.env` faylida saqlang.

## Database yangi jadvallari

Yangi dinamik tizim quyidagi jadvallardan foydalanadi:

- `vacancies`
- `regulations`
- `regulation_versions`
- `regulation_chunks`
- `vacancy_regulations`
- `training_materials`
- `question_banks`
- `admin_change_logs`

Mavjud nomzod va stajirovka jadvallariga `vacancy_id` va `regulation_version_snapshot` ustunlari avtomatik migration orqali qo‘shiladi.

## Clockster nazorati

Clockster kelib-ketish sync’i xodim qabul qilingan zahoti emas, **stajirovka va yakuniy test tugagandan keyin** ishga tushadi.

```env
CLOCKSTER_ENABLED=true
CLOCKSTER_API_BASE=https://api.clockster.com/company/v2/
CLOCKSTER_API_TOKEN=YANGI_TOKEN
CLOCKSTER_EMPLOYEES_ENDPOINTS=employees,people,users
CLOCKSTER_ATTENDANCE_ENDPOINTS=attendance,attendances,timesheets,checkins
CLOCKSTER_SYNC_INTERVAL_MINUTES=15
CLOCKSTER_LOOKBACK_DAYS=7
CLOCKSTER_MATCH_THRESHOLD=0.78
```

## Tekshirish

Loyiha ichidagi `tests/smoke_test.py` lokal smoke-test bazasida quyidagilarni tekshiradi:

- boshlang‘ich vakansiyalar va reglamentlar bazaga tushishi;
- yangi vakansiya yaratish va active ro‘yxatda ko‘rinishi;
- TXT reglament yuklash/versiyalash/rollback;
- vakansiya-reglament bog‘lash va snapshot;
- AI kalitisiz fallback orqali 20 dars va test materiallari yaratish;
- materiallarni faollashtirish;
- o‘zgarishlar logiga yozilishi;
- HTML matn xavfsizligi.

```bash
python tests/smoke_test.py
```

Real Telegram yuborish, OpenAI API chaqiruvi va Clockster API chaqiruvi faqat haqiqiy `.env` kalitlari bilan serverda ishlatilganda tekshiriladi.
