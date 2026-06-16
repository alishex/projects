"""
Bir martalik interaktiv login skripti.
Bu skript SIZNING shaxsiy Telegram akkountingizga kirish uchun session fayl yaratadi.
Terminalda ishga tushiring va so'ralganda:
  - Telefon raqamingizga kelgan tasdiqlash kodini kiriting
  - Agar 2FA (parol) yoqilgan bo'lsa, parolingizni kiriting

Session fayl (`user_session.session`) joriy papkada saqlanadi - buni hech kimga bermang,
bu fayl orqali akkountingizga to'liq kirish mumkin.
"""

import asyncio

from telethon import TelegramClient

import config


async def main() -> None:
    if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
        raise ValueError("Avval .env faylga TELEGRAM_API_ID va TELEGRAM_API_HASH ni kiriting (my.telegram.org)")
    if not config.TELEGRAM_PHONE:
        raise ValueError("Avval .env faylga TELEGRAM_PHONE ni kiriting (masalan +998901234567)")

    client = TelegramClient(config.TELEGRAM_SESSION_NAME, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    await client.start(phone=config.TELEGRAM_PHONE)
    me = await client.get_me()
    print(f"\n✅ Muvaffaqiyatli ulandi: {me.first_name} {me.last_name or ''} (@{me.username or '-'})")
    print(f"Session fayl yaratildi: {config.TELEGRAM_SESSION_NAME}.session")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
