import asyncio
import html
import logging
import tempfile
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message

import config
import media_transcriber
import memory_store
from claude_agent import ClaudeAgent
from telegram_client import TelegramToolset, create_client

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("telegram_ai_assistant.bot")

TELEGRAM_MSG_LIMIT = 4096


async def send_long_message(message: Message, text: str) -> None:
    text = text or "(bo'sh javob)"
    for i in range(0, len(text), TELEGRAM_MSG_LIMIT):
        chunk = text[i : i + TELEGRAM_MSG_LIMIT]
        try:
            await message.answer(chunk)
        except TelegramBadRequest:
            # Claude HTML formatda xato yuborgan bo'lsa - formatlashsiz yuboramiz
            await message.answer(chunk, parse_mode=None)


def is_owner(message: Message) -> bool:
    if not config.OWNER_USER_ID:
        return True
    return message.from_user is not None and message.from_user.id == config.OWNER_USER_ID


async def main() -> None:
    if not config.COMMAND_BOT_TOKEN:
        raise ValueError("COMMAND_BOT_TOKEN .env da topilmadi")
    if not config.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY .env da topilmadi")

    logger.info("Telegram user-session ulanmoqda...")
    user_client = await create_client()
    me = await user_client.get_me()
    logger.info("User session ulandi: %s (@%s)", me.first_name, me.username or "-")

    toolset = TelegramToolset(user_client)
    await toolset.refresh_dialogs()
    logger.info("Dialoglar yuklandi: %s ta", len(toolset._dialog_cache))

    agent = ClaudeAgent(toolset)

    bot = Bot(token=config.COMMAND_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def start_cmd(message: Message) -> None:
        if not is_owner(message):
            await message.answer("Kechirasiz, bu bot shaxsiy assistant va sizga mo'ljallanmagan.")
            return
        await message.answer(
            "Salom! 👋 Men sizning Telegram akkountingizni AI yordamida boshqaruvchi assistantman.\n\n"
            "Menga oddiy tilda topshiriq yozing, masalan:\n"
            "\"ALLMAX SMM guruhidagi oy davomida topshirgan hisobotlarimni yig'ib bitta oylik hisobot qilib ber\"\n\n"
            "Men kerakli guruhlarni topib, xabarlarni o'qib, natijani sizga qaytaraman."
        )

    @dp.message(Command("clear"))
    async def clear_cmd(message: Message) -> None:
        if not is_owner(message):
            return
        memory_store.clear_history(message.chat.id)
        await message.answer("Suhbat tarixi tozalandi. 🧹")

    @dp.message(Command("dialogs"))
    async def dialogs_cmd(message: Message) -> None:
        if not is_owner(message):
            return
        await toolset.refresh_dialogs()
        dialogs = await toolset.list_dialogs(limit=30)
        lines = [f"{html.escape(d['type'])}: {html.escape(d['title'])}" for d in dialogs]
        await send_long_message(message, "Chatlar ro'yxati (birinchi 30 ta):\n" + "\n".join(lines))

    async def process_task(message: Message, task_text: str) -> None:
        task_text = task_text.strip()
        if not task_text:
            return

        thinking = await message.answer("🤖 Bajarilmoqda, biroz kuting...")
        history = memory_store.load_history(message.chat.id)
        try:
            result = await agent.run_task(task_text, history=history)
            memory_store.append_turn(message.chat.id, task_text, result)
        except Exception as exc:
            logger.exception("Agent error: %s", exc)
            result = f"⚠️ Xatolik yuz berdi: {exc}"
        finally:
            try:
                await thinking.delete()
            except Exception:
                pass

        await send_long_message(message, result)

    @dp.message(F.text)
    async def handle_task(message: Message) -> None:
        if not is_owner(message):
            await message.answer("Kechirasiz, bu bot shaxsiy assistant va sizga mo'ljallanmagan.")
            return

        await process_task(message, message.text)

    @dp.message(F.photo)
    async def handle_photo_task(message: Message) -> None:
        if not is_owner(message):
            await message.answer("Kechirasiz, bu bot shaxsiy assistant va sizga mo'ljallanmagan.")
            return
        thinking = await message.answer("🖼 Rasm tahlil qilinmoqda...")
        try:
            import tempfile, base64
            from pathlib import Path
            photo = message.photo[-1]  # eng katta o'lcham
            with tempfile.TemporaryDirectory() as tmpdir:
                path = await bot.download(photo, destination=str(Path(tmpdir) / 'photo'))
                path = Path(path)
                mime = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                        '.png': 'image/png', '.webp': 'image/webp'}.get(path.suffix.lower(), 'image/jpeg')
                with open(path, 'rb') as f:
                    img_data = base64.standard_b64encode(f.read()).decode()
            from media_transcriber import _describe_image_sync
            import asyncio
            description = await asyncio.to_thread(_describe_image_sync, mime, img_data)
        except Exception as exc:
            description = f'Rasm tahlil xatosi: {exc}'
        finally:
            try:
                await thinking.delete()
            except Exception:
                pass
        caption = message.caption or ''
        task = f'[📸 Rasm: {description}]'
        if caption.strip():
            task += " Savol: " + caption
        await message.answer("🖼 " + html.escape(description))
        if caption.strip():
            await process_task(message, task)

    @dp.message(F.voice | F.video_note | F.video | F.audio)
    async def handle_voice_task(message: Message) -> None:
        if not is_owner(message):
            await message.answer("Kechirasiz, bu bot shaxsiy assistant va sizga mo'ljallanmagan.")
            return

        media = message.voice or message.video_note or message.video or message.audio
        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = Path(tmpdir) / "input.media"
            await bot.download(media, destination=str(src_path))
            try:
                task_text = await media_transcriber.transcribe_file(src_path)
            except Exception as exc:
                logger.exception("Ovozli xabarni transkripsiya qilishda xatolik: %s", exc)
                await message.answer("⚠️ Ovozli xabarni tushunolmadim, matn ko'rinishida yozib yuborolasizmi?")
                return

        await message.answer(f"🎤 Tushundim: <i>{html.escape(task_text)}</i>")
        await process_task(message, task_text)

    logger.info("Bot ishga tushdi (long polling)")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
