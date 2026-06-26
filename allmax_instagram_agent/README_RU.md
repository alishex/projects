# Instagram DM → Bitrix24 CRM / Project → Telegram Lead Notification Bot

Проект принимает сообщения из Instagram Direct через Meta Webhook, извлекает имя и номер телефона клиента, сохраняет состояние диалога в SQLite, создает лид в Bitrix24 CRM, при необходимости создает задачу в Bitrix24 Project/Tasks и отправляет уведомление в Telegram-группу.

## 1. Что делает проект

Цепочка работы:

`Instagram DM → Meta Webhook → FastAPI → Regex/OpenAI parser → SQLite → Bitrix24 CRM Lead → Bitrix24 Task → Telegram Lead Group`

Если клиент не оставил имя и телефон, бот отправляет шаблонное сообщение в Instagram DM:

> Murojatingiz qabul qilindi. Batafsil ma’lumot berishimiz uchun ism va raqamingizni yozib qoldiring. +998 78 555 31 31 raqamidan sizga bog‘lanamiz.

Бот не ведет длинный диалог. OpenAI используется только для извлечения имени и телефона.

## 2. Что понадобится

- Python 3.11+
- Meta Developer App
- Instagram Professional/Business account
- Публичный HTTPS URL для Meta webhook
- Inbound webhook Bitrix24
- Telegram bot token и chat ID группы
- OpenAI API key

## 3. Настройка `.env`

Создайте `.env` из примера:

```bash
cp .env.example .env
```

Основные параметры:

```env
META_VERIFY_TOKEN=your_custom_verify_token
META_APP_SECRET=your_meta_app_secret
META_IG_USER_ACCESS_TOKEN=your_instagram_user_access_token
META_IG_BUSINESS_ID=your_instagram_business_id
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-5.5-mini
BITRIX_WEBHOOK_URL=https://yourdomain.bitrix24.kz/rest/USER_ID/WEBHOOK_CODE
BITRIX_ASSIGNED_BY_ID=63
BITRIX_PROJECT_GROUP_ID=15
BITRIX_PROJECT_RESPONSIBLE_ID=63
LEAD_TELEGRAM_BOT_TOKEN=your_telegram_bot_token
LEAD_TELEGRAM_CHAT_ID=-100xxxxxxxxxx
```

Не храните реальные токены в коде. Файл `.env` находится в `.gitignore`.

## 4. Instagram Login mode

```env
META_API_MODE=instagram_login
META_IG_USER_ACCESS_TOKEN=...
META_IG_BUSINESS_ID=...
```

В этом режиме используется Instagram access token.

## 5. Facebook Page mode

```env
META_API_MODE=facebook_page
META_PAGE_ACCESS_TOKEN=...
META_PAGE_ID=...
META_IG_BUSINESS_ID=...
```

Если `META_IG_BUSINESS_ID` не указан, проект попробует получить его через Facebook Page.

## 6. Подключение Meta webhook

Callback URL:

```text
https://your-domain.com/webhook
```

Verify token должен совпадать с `META_VERIFY_TOKEN` из `.env`.

POST запросы проверяются через `X-Hub-Signature-256` и `META_APP_SECRET`.

## 7. Bitrix24 webhook

Создайте Incoming webhook в Bitrix24 с правами на CRM и задачи.

```env
BITRIX_WEBHOOK_URL=https://yourdomain.bitrix24.kz/rest/USER_ID/WEBHOOK_CODE
```

Используемые методы: `crm.lead.add`, `crm.lead.list`, `crm.status.list`, `crm.duplicate.findbycomm`, `tasks.task.add`.

## 8. Telegram bot token

1. Создайте бота через `@BotFather`.
2. Добавьте бота в Telegram-группу.
3. Дайте права администратора.
4. Укажите token и chat ID в `.env`.

```env
LEAD_TELEGRAM_BOT_TOKEN=...
LEAD_TELEGRAM_CHAT_ID=-100xxxxxxxxxx
```

## 9. Локальный запуск

Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Windows:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

## 10. Запуск на VPS

1. Загрузите проект на VPS.
2. Заполните `.env`.
3. Проверьте запуск через `python run.py`.
4. Для production используйте systemd, Supervisor или Docker Compose.
5. Подключите Nginx и HTTPS.

## 11. Docker запуск

```bash
cp .env.example .env
# заполните .env
docker compose up -d --build
```

Логи:

```bash
docker compose logs -f
```

## 12. Тест через Ngrok/cloudflared

```bash
python run.py
ngrok http 8000
```

Webhook URL:

```text
https://xxxx.ngrok-free.app/webhook
```

## 13. Endpoint-ы

- `GET /` — статус сервиса
- `GET /health` — health check
- `GET /webhook` — проверка Meta webhook
- `POST /webhook` — прием Instagram DM webhook

## 14. Логика дублей

Проект защищается от дублей:

1. `processed_events` — один webhook event не обрабатывается повторно.
2. `sent_leads` и `conversations` — один телефон не уходит повторно.
3. Bitrix24 duplicate check — поиск номера в CRM.

Настройки:

```env
BITRIX_DUPLICATE_SKIP_CRM_LEAD=true
BITRIX_DUPLICATE_SKIP_PROJECT_TASK=true
LEAD_TELEGRAM_SKIP_DUPLICATES=true
```

## 15. Target/реклама

Проверяются поля:

- `referral`
- `ad_id`
- `ad_title`
- `source`
- `postback`
- `metadata`
- keywords: `target,reklama,ads,ad,instagram target`

Если реклама определена, в Telegram появится строка 🎯, а лид/задача могут перейти в target status/stage.

## 16. Частые ошибки

**403 Invalid signature**  
Проверьте `META_APP_SECRET` и заголовок `X-Hub-Signature-256`.

**Не отправляется шаблон в Instagram**  
Проверьте Instagram Business ID и access token.

**Не создается лид Bitrix24**  
Проверьте webhook URL, права CRM и status ID.

**Telegram не отправляет сообщение**  
Проверьте chat ID и права бота в группе.

## 17. Troubleshooting

```bash
tail -f logs/app.log
tail -f logs/error.log
pytest
```

SQLite база:

```text
data/instagram_dm_bot.sqlite3
```

Для локального теста можно оставить `META_APP_SECRET=replace_me`, тогда signature verification будет bypass. В production обязательно укажите реальный secret.
