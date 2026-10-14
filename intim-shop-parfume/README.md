# INTIM SHOP — Dark Rose Collection

Qora va to‘q bordo uslubidagi intim tovarlar internet-do‘koni. Original SVG kampaniya grafikasi, 12 ta namuna mahsulot (UZ/RU/EN tarjima bilan), katalog, to‘plam yig‘ish, savat, mehmon sifatida buyurtma, buyurtmani maxsus havola orqali kuzatish, himoyalangan admin panel va Telegram xabarnomalari. Buyurtma va yetkazib berish diskret — mahsulot nomi tashqi qadoqda ko‘rsatilmaydi (jismoniy qadoqlash o‘zingiz tomondan ta’minlanadi).

## Eng tez ishga tushirish

1. Kompyuterga **Node.js 24 LTS yoki yangi versiya** o‘rnating: https://nodejs.org/
2. ZIPni oching va `intim-shop-parfume` papkasiga kiring.
3. Shu papkada terminal ochib yozing:

```sh
npm start
```

4. Brauzerda **http://localhost:3000** ni oching.
5. Administrator paneli: **http://localhost:3000/admin**.
6. Email: `admin@intimshop.local`. Birinchi ishga tushirishda tasodifiy admin paroli terminalda chiqadi. Uni saqlab oling.

`npm install` talab qilinmaydi: loyiha tashqi npm kutubxonalarisiz ishlaydi (Node 24'ning o‘rnatilgan `node:sqlite` moduli ishlatiladi). Internet bo‘lmasa ham do‘kon, admin va buyurtma bazasi ishlaydi. Telegram uchun internet kerak. `index.html`ni ikki marta bosib ochish backendni ishga tushirmaydi — yuqoridagi `npm start`ni ishlating.

Windowsda `BOSHLA.bat`, macOS/Linuxda `bash boshla.sh` ham shu serverni ishga tushiradi.

## Tuzilishi

- `public/` — tayyor HTML, CSS, JavaScript, original SVG grafika va favicon.
- `server.mjs` — HTTP server, API, statik fayllar, sessiyalar va xavfsizlik tekshiruvlari.
- `lib/store.mjs` — SQLite baza, mahsulotlar, variantlar, buyurtmalar va admin amallari.
- `lib/telegram.mjs` — Telegram xabarnoma navbati va qayta yuborish.
- `lib/bot.mjs` — Telegram bot admin menyusi (buyurtmalar, mahsulotlar, statistika).
- `migrations/001_initial.sql` — birinchi baza sxemasi, ishga tushganda avtomatik qo‘llanadi.
- `tests/` — Node testlari va haqiqiy HTTP orqali integratsiya testi.
- `data/` — birinchi ishga tushganda yaratiladi. Bazangiz va yuklangan rasmlar shu yerda.

Loyiha oson ko‘chirish uchun Node.js 24 + SQLite + oddiy JavaScript bilan yozilgan. Alohida PostgreSQL, Next.js build yoki pulli xizmat kerak emas. Bitta do‘kon serveri uchun mo‘ljallangan.

## Uch tilli interfeys (UZ / RU / EN)

Sayt interfeysi (navigatsiya, tugmalar, checkout, holat xabarlari) UZ/RU/EN tillarida ishlaydi; til tanlovi header'dagi **UZ / RU / EN** tugmalari orqali o‘zgaradi va brauzerda saqlanadi. Mahsulot nomi barcha tillarda bir xil qoladi (brend nomlari odatda tarjima qilinmaydi), tavsif/tarkib/parvarish matnlari esa har bir mahsulot uchun admin panelning "Tarjimalar (RU / EN)" bo‘limida ixtiyoriy ravishda kiritiladi — bo‘sh qoldirilsa, mijozga o‘zbekcha matn ko‘rsatiladi.

Server tomonidagi tekshiruv xabarlari (masalan, checkout validatsiyasi)da eng ko‘p uchraydigan holatlar RU/EN'ga ham tarjima qilingan (`public/app.js` ichidagi `ERROR_MAP`); admin panel esa operator uchun mo‘ljallangani sababli faqat o‘zbekcha.

## Brend va mahsulotlarni o‘zgartirish

`public/brand.json` ichida nom, tagline, telefon, Telegram/Instagram havolalari, manzil va yetkazish matni bor. Bo‘sh kontakt maydonlari ataylab to‘ldirilmagan — o‘zingiznikini kiriting.

Mahsulotlar uchun `/admin`ga kiring:

- Yangi mahsulot qo‘shing yoki mavjudini tahrirlang.
- Toifa, narx, tavsif, hid tarkibi va saqlash shartini kiriting.
- O‘lcham (masalan "S/M/L" yoki "Standart") va rang bo‘yicha variantlarni hamda har birining ombor qoldig‘ini belgilang.
- JPG, PNG yoki WebP rasm yuklang: har biri 5 MB gacha, mahsulotga ko‘pi bilan 6 ta.
- Keraksiz mahsulotni arxivlang. Eski buyurtmalardagi tarix yo‘qolmaydi.

**Muhim:** 12 ta namuna mahsulotning rasmlari original SVG grafika — haqiqiy mahsulot fotosuratlari emas (loyihani tayyorlagan muhitda AI-rasm generatsiya vositasi mavjud emas edi). Har bir mahsulot alohida, bir-biridan farqli grafikaga ega, lekin ishga tushirishdan oldin **admin panel orqali haqiqiy mahsulot fotosuratlarini yuklashingiz tavsiya etiladi**. Narx, tarkib va saqlash ma’lumotlari ham namuna — haqiqiy assortiment kiritilgach `.env`da `DEMO_MODE=false` qiling.

## Telegramni ulash

1. Telegramdagi rasmiy **@BotFather** orqali `/newbot` buyrug‘i bilan bot yarating.
2. Botga o‘z Telegramingizdan `/start` yuboring yoki botni buyurtmalar uchun guruhga qo‘shing va xabar yuborish huquqini bering.
3. `.env.example`dan `.env` nusxa yarating.
4. `TELEGRAM_BOT_TOKEN` va `TELEGRAM_CHAT_ID`ni kiriting. Tokenni chatga, frontendga yoki Gitga joylamang.
5. Serverni to‘xtatib, qayta `npm start` qiling.
6. Sinov buyurtmasi berib, bazadagi buyurtma raqami Telegram xabaridagi raqam bilan mosligini tekshiring.

Chat IDni olish: bot bilan suhbat boshlanganidan keyin Telegram Bot API `getUpdates` javobidagi `message.chat.id`dan foydalanish mumkin. Tokenni faqat o‘z kompyuteringizda ishlating. Guruh IDsi manfiy son bo‘lishi mumkin.

Minimal `.env`:

```dotenv
PORT=3000
HOST=127.0.0.1
PUBLIC_URL=http://localhost:3000
ADMIN_EMAIL=admin@intimshop.local
ADMIN_PASSWORD=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DEMO_MODE=true
COOKIE_SECURE=false
TRUST_PROXY=false
```

`ADMIN_PASSWORD` bo‘sh bo‘lsa, birinchi ishga tushirishda kuchli parol yaratiladi. O‘zingiz belgilasangiz, kamida 12 belgi bo‘lsin. Keyin parolni yangilash:

```sh
node scripts/reset-admin.mjs
```

## Buyurtma qanday ishlaydi

Katalog → mahsulot va variant (hajm/nashr) → savat → ism, telefon, manzil → server narx va qoldiq tekshiruvi → tranzaksiya bilan buyurtma saqlash va qoldiq kamaytirish → Telegram navbati → tasdiq va maxsus kuzatish havolasi.

- Bir xil so‘rov kaliti bilan qayta urinish yangi buyurtma yaratmaydi.
- Bir xil kalit bilan o‘zgartirilgan buyurtma rad etiladi.
- Frontend yuborgan narx hisobga olinmaydi — narx har doim serverda, bazadan qayta hisoblanadi.
- Qoldiq yetmasa buyurtma yaratilmaydi; qisman o‘zgarishlar qaytariladi.
- Bekor qilish qoldiqni bir marta qaytaradi.
- Eski buyurtma nomlari va narxlari katalog o‘zgarganda o‘zgarmaydi (snapshot).
- Kuzatish havolasidagi maxsus kod faqat buyurtma tafsilotlarini beradi; telefon va manzil qaytarmaydi.

To‘lov onlayn olinmaydi (yetkazib berganda naqd). Yetkazish narxi va to‘lov shartlarini sotuvchi kelishadi. Click/Payme integratsiyasi va kuryer API bu paketga kiritilmagan.

## Telegram worker

Server ichidagi worker har 5 soniyada doimiy bazadagi navbatni tekshiradi. Xatoda eksponensial kutish bilan 5 martagacha qayta urinish bor. Oxirgi xato admin panelida ko‘rinadi va administrator qayta yuborishni boshlashi mumkin. Token sozlanmagan bo‘lsa, buyurtmalar saqlanadi va xabarlar navbatda qoladi.

## Telegram orqali boshqaruv (bot admin menyusi)

Web admin panelga qo‘shimcha ravishda, do‘konni **to‘liq Telegram bot orqali** ham boshqarish mumkin — faqat `.env`dagi `TELEGRAM_CHAT_ID`ga mos chatdan. Botga `/start` yuboring:

- **📦 Buyurtmalar** — ro‘yxat (sahifalab), har birini ochib mijoz/telefon/manzil/xaritadagi joylashuv/mahsulotlarni ko‘rish, holatni almashtirish (Yangi → Tasdiqlangan → Tayyorlanmoqda → Yetkazilgan, yoki Bekor qilish), muvaffaqiyatsiz xabarnomani qayta yuborish.
- **🛍 Mahsulotlar** — ro‘yxat, har birini ochib narxni yoki har bir variantning ombor qoldig‘ini tezda o‘zgartirish (bot "Yangi qiymatni kiriting" deb so‘raydi, siz shunchaki raqam yozasiz), faol/arxiv holatini almashtirish.
- **📊 Statistika** — yangi buyurtmalar soni, faol mahsulotlar soni, yetkazilgan buyurtmalar summasi.

Yangi mahsulot qo‘shish, tavsif/rasm/variant tuzilmasini tahrirlash kabi ko‘p-bosqichli amallar — qulaylik uchun web admin panelda (`/admin`) qoladi.

Buyurtma kelganda yuboriladigan xabardagi **✓ Tasdiqlash / ✗ Rad etish** tugmalari ham shu botning bir qismi — ularni bossangiz, buyurtma holati darhol yangilanadi va o‘sha xabar o‘zi yangilanadi (boshqa joydan, masalan bot menyusi yoki web admin orqali holat o‘zgarsa ham, asl xabar avtomatik yangilanadi).

## Hosting

Bu statik HTML hosting emas. Node.js 24 ishlaydigan VPS yoki Docker xizmati va **doimiy disk** kerak.

Docker bilan:

```sh
docker compose up --build -d
docker compose logs intimshop
```

Domen ulaganda:

1. HTTPS reverse proxy orqali ilovani yo‘naltiring.
2. `.env`da `PUBLIC_URL=https://sizning-domen.uz` ni qo‘ying.
3. HTTPS uchun `COOKIE_SECURE=true`.
4. Ishonchli reverse proxy ortida `TRUST_PROXY=true`; Node portini bevosita internetga ochmang.
5. Real tovarlar, kontaktlar, yetkazish shartlari va maxfiylik/qaytarish qoidalarini do‘koningizga mos kiriting.

## Zaxira nusxa

Serverni to‘xtatib `data/` papkasini nusxalang. Yangi serverda shu `data/` papkasini loyiha yoniga qo‘ysangiz mahsulotlar, buyurtmalar, administrator va rasmlar tiklanadi. Uni Gitga yoki ommaviy arxivga qo‘shmang.

## Tekshiruvlar

```sh
npm run check
npm test
```
