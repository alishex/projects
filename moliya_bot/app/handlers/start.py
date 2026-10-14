from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.config import OWNER_ID
from app.keyboards import main_menu

router = Router()
router.message.filter(F.from_user.id == OWNER_ID)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Ассалому алайкум! Молиявий трекер боти тайёр.\n\n"
        "Тугмалардан фойдаланинг ёки оддийгина ёзинг/овозли хабар юборинг, "
        "масалан: <i>«таксига 50 минг нақд кетди»</i> — мен ўзим тушуниб, қайд этаман.",
        reply_markup=main_menu(),
    )


@router.message(F.text == "/cancel")
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Бекор қилинди.", reply_markup=main_menu())
