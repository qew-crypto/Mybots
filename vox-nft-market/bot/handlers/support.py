from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from bot.keyboards import back_to_menu_kb

router = Router()

SUPPORT_TEXT = (
    "◈ <b>Поддержка</b>\n"
    "━━━━━━━━━━━━━━━━━━━\n\n"
    "По любым вопросам обращайтесь:\n\n"
    "💬 @VoxNFTSupport\n\n"
    "Среднее время ответа: 5 минут\n"
    "Работаем 24/7"
)


@router.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery):
    await callback.message.edit_text(SUPPORT_TEXT, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.message(Command("support"))
async def cmd_support(message: Message):
    await message.answer(SUPPORT_TEXT, reply_markup=back_to_menu_kb(), parse_mode="HTML")
