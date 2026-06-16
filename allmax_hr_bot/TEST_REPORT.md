# Lokal tekshiruv natijasi

Ushbu build zipga joylashdan oldin lokal test muhitida tekshirildi.

## Tekshirilgan holatlar

- Python modullarining syntax/compile tekshiruvi (`python -m compileall`).
- Router va keyboard modullarining import qilinishi.
- Boshlang‘ich vakansiyalar va DOCX reglamentlar bazaga avtomatik import qilinishi.
- Yangi vakansiyani DB orqali qo‘shish va `active` ro‘yxatda paydo bo‘lishi.
- TXT reglamentni o‘qish, `v1` va `v2` versiyalarini saqlash, yangi versiyani faollashtirish va `v1` ga rollback.
- Vakansiya–reglament bog‘lanishi va `regulation_version_snapshot` saqlanishi.
- OpenAI kalitisiz fallback rejimida 10 ta intervyu savoli, 20 ta dars, 200 ta dars test savoli va 30 ta yakuniy test savoli draft sifatida yaratilishi.
- Material batch’ini `active` holatiga o‘tkazish.
- Boshlangan stajirovka keyingi reglament versiyasi faollashganda ham o‘z snapshotini saqlab qolishi.
- Telegram HTML parse xatosiga sabab bo‘lgan `<...>` matnlar HTML-escape qilinishi.
- GPT-5.5/reasoning modeliga `temperature=0.2` yuborilmasligi bo‘yicha parameter guard testi.
- Admin o‘zgarishlari loglarda saqlanishi.

## Buyruqlar

```bash
python -m compileall -q app main.py tests
python tests/smoke_test.py
python tests/openai_parameter_guard_test.py
```

## Serverda haqiqiy kalitlar bilan tekshiriladigan qismlar

Telegramga real xabar yuborish, OpenAI API’dan real javob olish va Clockster API’dan kelib-ketish ma’lumotlarini olish uchun haqiqiy `.env` qiymatlari kerak. Tokenlar ushbu zip ichiga kiritilmagan.
