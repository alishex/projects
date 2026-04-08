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
