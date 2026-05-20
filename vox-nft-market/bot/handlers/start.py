from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command

from bot.database import create_user, get_user, is_banned, add_log
from bot.keyboards import main_menu_kb

router = Router()

WELCOME_TEXT = (
    "◈ <b>Vox NFT Market</b>\n"
    "━━━━━━━━━━━━━━━━━━━\n\n"
    "Автоматический выкуп NFT-подарков\n"
    "по лучшей цене.\n\n"
    "◈ Моментальная оценка\n"
    "◈ Безопасные сделки\n"
    "◈ Быстрый вывод\n\n"
    "━━━━━━━━━━━━━━━━━━━\n"
    "Выберите действие:"
)

BANNED_TEXT = "⛔ Ваш аккаунт ограничен. Обратитесь в поддержку."


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    await create_user(user.id, user.username or "", user.first_name or "")
    await add_log(user.id, "start", "Запуск бота")

    if await is_banned(user.id):
        await message.answer(BANNED_TEXT)
        return

    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer(BANNED_TEXT, show_alert=True)
        return

    await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu_kb(), parse_mode="HTML")
    await callback.answer()
