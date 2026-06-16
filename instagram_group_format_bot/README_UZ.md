# Instagram DM → Bitrix24 Contact Capture Bot

Bu loyiha Instagram DM uchun tayyor webhook-server dasturi. Endi u 2 xil Meta rejimida ishlay oladi: Facebook Page flow va Instagram Login flow.

## Nima qiladi
- mijoz DM yozsa chatni kuzatadi
- AI faqat ism va telefon raqamni ajratish uchun ishlaydi
- AI mijozga javob yozmaydi
- kontakt hali topilmagan bo‘lsa faqat bitta shablon yuboradi
- mijoz qancha yozsa ham ism + telefon topilmaguncha shu shablon ishlaydi
- agar siz tomondan manual xabar yozilgan bo‘lsa template to‘xtaydi, lekin monitoring davom etadi
- ism + telefon topilishi bilan Bitrix24 ga darhol lead yaratadi
- xohlasangiz Telegram lead group’ga ham yuboradi
- SQLite ichida chat state saqlanadi

## Muhim
Instagram DM uchun bu loyiha rasmiy Meta API asosida yozilgan va 2 xil ishlash rejimini qo‘llaydi:
- **Instagram Login mode** — tavsiya etiladi, Facebook Page ID topishda qiynalayotganlar uchun qulay
- **Facebook Page mode** — avvalgi klassik usul

## Kerak bo‘ladigan narsalar
1. Instagram Professional account
2. Meta App
3. Webhook public URL
4. OpenAI API key
5. Bitrix webhook

### Variant A — Instagram Login mode
- `META_IG_USER_ACCESS_TOKEN`
- `META_IG_BUSINESS_ID`
- Facebook Page majburiy emas

### Variant B — Facebook Page mode
- `META_PAGE_ACCESS_TOKEN`
- `META_PAGE_ID`
- `META_IG_BUSINESS_ID` ixtiyoriy, kod o‘zi topishga urinadi
- ulangan Facebook Page kerak

## O‘rnatish
1. Papkani kompyuterga ko‘chiring
2. `.env.example` ni nusxa olib `.env` qiling
3. `.env` ichiga token va ID larni yozing
4. Terminalda ishga tushiring:

```bash
pip install -r requirements.txt
python app.py
```

Windows uchun:
- `start_instagram_bot.bat` ni ishga tushirsangiz ham bo‘ladi

## Webhook URL
Server ishga tushgandan keyin quyidagilar kerak bo‘ladi:
- verify URL: `https://sizning-domeningiz/webhook`
- verify token: `.env` ichidagi `META_VERIFY_TOKEN`

Local test uchun ngrok yoki cloudflared ishlatishingiz mumkin.

## Meta dashboard tomonda
Webhook subscribe qilinadigan eventlar:
- messages
- messaging_seen
- message_reactions

Agar echo/outgoing eventlar sizga kelmasa, `ENABLE_CONVERSATION_SYNC=true` qoldiring. Shunda dastur Conversations API orqali so‘nggi chatlarni periodik tekshiradi va manual outgoing xabarlarni ham ushlab qolishga harakat qiladi.

## Asosiy logika
### 1. Incoming DM
Instagram webhookga yangi DM tushadi.

### 2. Monitoring
Dastur bu foydalanuvchi bo‘yicha state ochadi yoki mavjud state ni o‘qiydi.

### 3. AI parsing
Xabar va so‘nggi inbound tarixdan ism + telefon topishga urinadi.

### 4. Kontakt topilmasa
Agar manual outgoing flag yo‘q bo‘lsa, faqat bitta shablon yuboradi.

### 5. Manual outgoing bo‘lsa
Template yubormaydi, lekin yozishmalarni kuzatishda davom etadi.

### 6. Kontakt topilsa
Darhol Bitrix24 ga lead qiladi.

## Foydali .env maydonlari
- `META_PAGE_ID` — ulangan Facebook Page ID
- `META_IG_BUSINESS_ID` — Instagram Business ID
- `META_PAGE_ACCESS_TOKEN` — Page access token
- `OPENAI_API_KEY` — contact parser uchun
- `BITRIX_WEBHOOK_URL` — Bitrix webhook

## Endpointlar
- `GET /health`
- `GET /webhook`
- `POST /webhook`

## Eslatma
Instagram tarafda manual inbox orqali yozilgan xabarlarni kuzatish Meta konfiguratsiyasiga bog‘liq bo‘lishi mumkin. Shu sabab kod ichida ikki qatlam bor:
1. webhook echo/outgoing detect
2. Conversations API sync

Shu ikki qatlam birga ishlaganda siz so‘ragan “biz yozsak template yozmasin, lekin kuzatib borsin” mantiqiga yaqinlashadi.


## Tavsiya etilgan .env konfiguratsiya
### Instagram Login mode
```env
META_API_MODE=instagram_login
META_VERIFY_TOKEN=replace_me
META_IG_USER_ACCESS_TOKEN=replace_me
META_IG_BUSINESS_ID=replace_me
GRAPH_API_VERSION=v23.0
```

### Facebook Page mode
```env
META_API_MODE=facebook_page
META_VERIFY_TOKEN=replace_me
META_PAGE_ACCESS_TOKEN=replace_me
META_PAGE_ID=replace_me
META_IG_BUSINESS_ID=replace_me
GRAPH_API_VERSION=v23.0
```

## Nima o‘zgardi
- TZ dagi mantiq saqlandi
- AI faqat ism va telefon aniqlaydi
- bitta template qayta yuboriladi
- operator birinchi yozsa template to‘xtaydi
- monitoring va Bitrix upsert saqlandi
- endi dastur Instagram Login flow bilan ham ishlay oladi
- `META_PAGE_ACCESS_TOKEN` bo‘lmasa ham Instagram Login token bilan ishlashi mumkin


## Bitrix Instagram stage/source sozlamasi

Ushbu versiyada Instagram orqali kelgan yangi leadlar Bitrix'dagi `Instagram` stadiyasiga tushishi uchun quyidagi sozlamalar qo'shilgan:

```env
BITRIX_LEAD_TITLE_PREFIX=INSTAGRAM
BITRIX_SOURCE_ID=INSTAGRAM
BITRIX_SOURCE_NAME=Instagram
BITRIX_LEAD_STATUS_ID=UC_SURQ0Z
BITRIX_LEAD_STATUS_NAME=Instagram
BITRIX_FORCE_INSTAGRAM_IN_TITLE=true
```

Sizning Bitrix ro'yxatingizdagi Instagram stage: `NAME=Instagram`, `STATUS_ID=UC_SURQ0Z`.
Kod ishga tushganda `crm.status.list` orqali `STATUS` va `SOURCE` ro'yxatini tekshiradi. Agar `SOURCE_ID` ichki ID boshqacha bo'lsa, `SOURCE_NAME=Instagram` bo'yicha topishga harakat qiladi.

Bitrix ichida oddiy qidiruvda ham chiqishi uchun lead `TITLE` qismiga `INSTAGRAM` so'zi majburiy qo'shiladi.

## Yangi qo‘shimcha: Instagram DM → Bitrix24 Project task

Ushbu tayyorlangan versiyada Instagramdan ism + telefon aniqlangandan keyin faqat CRM lead ochish bilan cheklanmaydi. Endi Bitrix24 `Zadachi i Proyekti` ichidagi kerakli projectga ham task ochadi.

Siz tekshirgan project ma’lumotlari:

```env
BITRIX_PROJECT_GROUP_ID=15
BITRIX_PROJECT_STAGE_ID=301
```

`303` — project ichidagi `Instagram` ustuni ID si. Instagram leadlar shu ustunga tushadi.

### Project uchun .env sozlamalar

```env
BITRIX_PROJECT_ENABLE=true
BITRIX_PROJECT_GROUP_ID=15
BITRIX_PROJECT_RESPONSIBLE_ID=63
BITRIX_PROJECT_STAGE_ID=301
BITRIX_PROJECT_TASK_TITLE_PREFIX=Instagram lead
BITRIX_PROJECT_TASK_DEADLINE_HOURS=0
BITRIX_PROJECT_BIND_TO_CRM=true
```

Ma’nosi:
- `BITRIX_PROJECT_ENABLE=true` — projectga task ochishni yoqadi
- `BITRIX_PROJECT_GROUP_ID=15` — Bitrix project ID
- `BITRIX_PROJECT_RESPONSIBLE_ID=63` — task mas’ul xodim ID
- `BITRIX_PROJECT_STAGE_ID=301` — task tushadigan Kanban ustuni, sizda `Telegram`
- `BITRIX_PROJECT_TASK_TITLE_PREFIX=Instagram lead` — task nomi boshidagi matn
- `BITRIX_PROJECT_TASK_DEADLINE_HOURS=0` — deadline qo‘yilmaydi
- `BITRIX_PROJECT_BIND_TO_CRM=true` — taskni yaratilgan CRM lead bilan bog‘lashga urinadi

### Dublikat tekshirish

Bu versiyada dublikat tekshirish kuchaytirildi:

```env
BITRIX_DUPLICATE_CHECK_ENABLE=true
BITRIX_DUPLICATE_SKIP_PROJECT_TASK=true
BITRIX_DUPLICATE_SKIP_CRM_LEAD=true
```

Ma’nosi:
- Telefon bo‘yicha Bitrix CRM ichidan dublikat qidiradi
- Shu telefon oldin shu SQLite bazada yuborilgan bo‘lsa ham dublikat deb ko‘radi
- Dublikat topilsa yangi CRM lead ochmaydi
- Dublikat topilsa yangi project task ham ochmaydi
- Dublikat ma’lumoti SQLite ichidagi `bitrix_duplicate_info` ustunida saqlanadi

Agar dublikat bo‘lsa ham projectga alohida task ochilsin desangiz:

```env
BITRIX_DUPLICATE_SKIP_PROJECT_TASK=false
```

Agar CRM lead ochilmasin, lekin faqat project task ochilsin desangiz:

```env
BITRIX_ENABLE=false
BITRIX_PROJECT_ENABLE=true
```



## Yangi qo‘shimcha: Instagram leadlarni Telegram guruhga yuborish

Ushbu versiyada Instagram DM orqali ism + telefon aniqlangandan keyin bot Telegram guruhga ham xabar yuboradi. Xabar CRM/project ishlovidan keyin yuboriladi, shuning uchun unda CRM lead ID va Project task ID ham chiqadi.

`.env` ichida quyidagilarni to‘ldiring:

```env
LEAD_TELEGRAM_ENABLE=true
LEAD_TELEGRAM_BOT_TOKEN=telegram_bot_token_here
LEAD_TELEGRAM_CHAT_ID=-100xxxxxxxxxx
LEAD_TELEGRAM_SKIP_DUPLICATES=true
```

Ma’nosi:
- `LEAD_TELEGRAM_ENABLE=true` — Telegram guruhga xabar yuborishni yoqadi
- `LEAD_TELEGRAM_BOT_TOKEN` — BotFather’dan olingan Telegram bot token
- `LEAD_TELEGRAM_CHAT_ID` — leadlar tushadigan Telegram guruh ID si
- `LEAD_TELEGRAM_SKIP_DUPLICATES=true` — dublikat telefon topilsa guruhga qayta yubormaydi

Telegram guruhga keladigan xabar namunasi:

```text
🆕 YANGI INSTAGRAM LEAD

👤 Ism: Ali
📞 Telefon: +998901234567
📌 Manba: Instagram DM
🧑‍💻 Instagram nik: @username
🏷 CRM lead ID: 456
📋 Project task ID: 789
📊 Holat: created_or_project_updated

💬 Mijoz xabari:
Ali +998901234567
```

Eslatma: Bot guruhga yozishi uchun Telegram botni o‘sha guruhga qo‘shing va kerak bo‘lsa admin qiling.

## Telegram guruh xabari formati

Ushbu versiyada Instagramdan kelgan yangi lead Telegram guruhga Bitrix24 call lead xabari uslubida yuboriladi:

- 🆕 Yangi lead tushdi
- 👤 Mas’ul
- 🆔 Lead ID
- 📌 Nomi
- 🙋 Mijoz ismi
- 📞 Telefon
- ✉️ Email
- 📍 Manba
- 📊 Status
- 👨‍💼 Bitrix mas’ul ID
- 🕒 Vaqt
- 🔗 Bitrix24’da ochish

Qo‘shimcha sozlamalar `.env` ichida:

```env
LEAD_TELEGRAM_RESPONSIBLE_NAME=
LEAD_TELEGRAM_SOURCE_TEXT=Instagram DM
LEAD_TELEGRAM_STATUS_TEXT=Instagram
LEAD_TELEGRAM_TIMEZONE_OFFSET_HOURS=5
LEAD_TELEGRAM_PHONE_FORMAT=local
```

`LEAD_TELEGRAM_RESPONSIBLE_NAME` bo‘sh qolsa, bot Bitrix24 `user.get` orqali mas’ul xodim nomini avtomatik olishga harakat qiladi.


## Yangilanish: IGSID o‘rniga Instagram nik

Ushbu versiyada Bitrix24 CRM lead kommenti, Project task tavsifi va Telegram guruh xabarida endi `IGSID` ko‘rsatilmaydi. Bot imkon qadar mijozning Instagram nikini oladi va quyidagi formatda yozadi:

```text
Instagram nik: @username
```

Lead nomida ham nick ishlatilishi uchun `.env`da quyidagi sozlama qo‘shilgan:

```env
BITRIX_USE_INSTAGRAM_NICK_IN_TITLE=true
```

Agar Meta API nickni qaytarmasa, maydon `—` bo‘lib qoladi, lekin IGSID Bitrix komment/description ichiga yozilmaydi.

## Yangi qo‘shimcha: Target video leadlarni alohida stagega yig‘ish

Ushbu versiyada Instagram target/reklama videolaridan kelgan DMlar alohida aniqlanadi. Agar Meta webhook payload ichida reklama/ad/video referral ma’lumoti bo‘lsa, bot:

- CRM lead kommentiga target video nomini qo‘shadi
- Project task description ichiga target video nomini qo‘shadi
- Telegram guruh xabarida `🎯 Target video` qatorini chiqaradi
- kerak bo‘lsa project ichida boshqa Kanban stagega tashlaydi
- kerak bo‘lsa CRM leadni boshqa lead status/stagega tashlaydi

`.env` ichiga qo‘shiladigan sozlamalar:

```env
TARGET_VIDEO_DETECTION_ENABLE=true

# Project ichidagi target video uchun alohida ustun ID si.
# Bitrix task.stages.get orqali olasiz. 0 bo‘lsa oddiy Instagram stage ishlaydi.
BITRIX_TARGET_PROJECT_STAGE_ID=0

# CRM lead ichidagi target video status/stage. Bo‘sh bo‘lsa oddiy Instagram status ishlaydi.
BITRIX_TARGET_LEAD_STATUS_ID=
BITRIX_TARGET_LEAD_STATUS_NAME=Target video

BITRIX_TARGET_TASK_TITLE_PREFIX=Target video lead
TARGET_VIDEO_DEFAULT_NAME=Target video
TARGET_VIDEO_KEYWORDS=target,reklama,ads
LEAD_TELEGRAM_TARGET_STATUS_TEXT=Target video
```

Target video stage ID olish uchun avval Bitrix24 Project ichida alohida ustun yarating, masalan: `Target video`. Keyin terminalda:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"entityId":15}' \
  "https://allmax.bitrix24.kz/rest/USER_ID/WEBHOOK_CODE/task.stages.get"
```

Natijadan `TITLE="Target video"` bo‘lgan qatorning `ID` qiymatini oling va `.env`ga qo‘ying:

```env
BITRIX_TARGET_PROJECT_STAGE_ID=TARGET_STAGE_ID_SHU_YERGA
```

CRM lead uchun ham alohida status kerak bo‘lsa, lead statuslar ro‘yxatini oling:

```bash
curl -s -X POST \
  -d "filter[ENTITY_ID]=STATUS" \
  "https://allmax.bitrix24.kz/rest/USER_ID/WEBHOOK_CODE/crm.status.list.json" | jq -r '.result[] | "\(.STATUS_ID) - \(.NAME)"'
```

Keyin target video statusining `STATUS_ID` qiymatini `.env`ga yozing:

```env
BITRIX_TARGET_LEAD_STATUS_ID=UC_XXXXXX
```

Agar Meta target video nomini qaytarsa, kommentda shunaqa chiqadi:

```text
Target video ma’lumoti:
Target video nomi: 2026 yozgi aksiya video
Target video ID: 123456789
Target video link: https://...
```
