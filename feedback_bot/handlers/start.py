import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from keyboards.menu import main_menu

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def start_cmd(message: Message):
    logger.info("Start: user_id=%s", message.from_user.id)
    await message.answer(
        "Assalomu alaykum! 👋\n\n"
        "Botimiz orqali fikr va mulohazalaringizni biz bilan baham ko'ring!\nEslatma: birgina taklifingiz — xizmatimizni yaxshilashga hissa qo'shadi.\n\n"
        "Boshlash uchun pastdagi tugmani bosing 👇",
        reply_markup=main_menu()
    )


@router.message(F.text == "/chatid")
async def chat_id(message: Message):
    await message.answer(f"<code>{message.chat.id}</code>", parse_mode="HTML")
