import time
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.database import (
    get_user, create_user, is_banned, get_user_deals,
    create_withdrawal, deduct_balance, add_log,
)
from bot.keyboards import profile_kb, withdraw_methods_kb, back_to_profile_kb, back_to_menu_kb

router = Router()


class WithdrawStates(StatesGroup):
    waiting_details = State()


WITHDRAW_PROMPTS = {
    "sbp": "📱 Введите номер телефона и банк для выплаты через СБП.",
    "card": "💳 Введите номер карты для выплаты.",
    "usdt": "💵 Введите USDT-адрес и сеть (TRC-20 / ERC-20).",
    "ton": "💠 Введите TON-кошелёк для выплаты.",
    "intl_card": "🌍 Введите данные для международного перевода.",
}

METHOD_NAMES = {
    "sbp": "СБП",
    "card": "Банковская карта",
    "usdt": "USDT",
    "ton": "TON",
    "intl_card": "Зарубежная карта",
}


def _format_date(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y")


async def _show_profile(callback_or_message, user_id: int, edit: bool = True):
    user = await get_user(user_id)
    if not user:
        text = "❌ Профиль не найден. Нажмите /start."
        if edit and hasattr(callback_or_message, "message"):
            await callback_or_message.message.edit_text(text)
        else:
            target = callback_or_message if isinstance(callback_or_message, Message) else callback_or_message.message
            await target.answer(text)
        return

    reg_date = _format_date(user["created_at"]) if user["created_at"] else "—"
    status = "🚫 Заблокирован" if user["is_banned"] else "Активен"

    text = (
        f"◈ <b>Ваш профиль</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"💰 Баланс: <b>{user['balance']:.2f} ₽</b>\n"
        f"📦 Продано NFT: <b>{user['sold_count']}</b>\n"
        f"💵 Всего получено: <b>{user['total_earned']:.2f} ₽</b>\n"
        f"📊 Статус: <b>{status}</b>\n"
        f"📅 Регистрация: {reg_date}"
    )

    if edit and hasattr(callback_or_message, "message"):
        await callback_or_message.message.edit_text(text, reply_markup=profile_kb(), parse_mode="HTML")
    elif isinstance(callback_or_message, Message):
        await callback_or_message.answer(text, reply_markup=profile_kb(), parse_mode="HTML")
    else:
        await callback_or_message.message.edit_text(text, reply_markup=profile_kb(), parse_mode="HTML")


@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _show_profile(callback, callback.from_user.id)
    await callback.answer()


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext):
    await state.clear()
    await create_user(message.from_user.id, message.from_user.username or "", message.from_user.first_name or "")
    await _show_profile(message, message.from_user.id, edit=False)


@router.callback_query(F.data == "deal_history")
async def cb_deal_history(callback: CallbackQuery):
    deals = await get_user_deals(callback.from_user.id, limit=10)
    if not deals:
        await callback.message.edit_text(
            "📋 У вас пока нет сделок.", reply_markup=back_to_profile_kb(), parse_mode="HTML"
        )
        await callback.answer()
        return

    status_map = {
        "awaiting_transfer": "⏳ Ожидает передачу",
        "checking": "🔄 Проверяется",
        "completed": "✅ Завершена",
        "cancelled": "❌ Отменена",
        "error": "⚠️ Ошибка",
    }

    lines = ["◈ <b>История продаж</b>\n━━━━━━━━━━━━━━━━━━━\n"]
    for d in deals:
        st = status_map.get(d["status"], d["status"])
        date = _format_date(d["created_at"])
        lines.append(f"#{d['id']} | {d['nft_name']} | {d['price_rub']} ₽ | {st} | {date}")

    await callback.message.edit_text(
        "\n".join(lines), reply_markup=back_to_profile_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "withdraw")
async def cb_withdraw(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or user["balance"] <= 0:
        await callback.answer("💰 Недостаточно средств для вывода.", show_alert=True)
        return

    text = (
        f"◈ <b>Вывод средств</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Доступно: <b>{user['balance']:.2f} ₽</b>\n\n"
        f"Выберите способ выплаты:"
    )
    await callback.message.edit_text(text, reply_markup=withdraw_methods_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("withdraw_method:"))
async def cb_withdraw_method(callback: CallbackQuery, state: FSMContext):
    method = callback.data.split(":")[1]
    user = await get_user(callback.from_user.id)
    if not user or user["balance"] <= 0:
        await callback.answer("💰 Недостаточно средств.", show_alert=True)
        return

    prompt = WITHDRAW_PROMPTS.get(method, "Введите реквизиты.")

    await state.set_state(WithdrawStates.waiting_details)
    await state.update_data(method=method, amount=user["balance"])

    await callback.message.edit_text(
        f"◈ <b>Вывод — {METHOD_NAMES.get(method, method)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Сумма: <b>{user['balance']:.2f} ₽</b>\n\n"
        f"{prompt}",
        reply_markup=back_to_profile_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(WithdrawStates.waiting_details)
async def process_withdraw_details(message: Message, state: FSMContext):
    data = await state.get_data()
    method = data.get("method", "")
    amount = data.get("amount", 0)

    if not message.text or len(message.text.strip()) < 3:
        await message.answer("❌ Введите корректные реквизиты.")
        return

    details = message.text.strip()

    success = await deduct_balance(message.from_user.id, amount)
    if not success:
        await message.answer("❌ Недостаточно средств.")
        await state.clear()
        return

    withdrawal_id = await create_withdrawal(message.from_user.id, amount, method, details)
    await add_log(message.from_user.id, "withdrawal_created", f"#{withdrawal_id} | {amount} ₽ | {method}")

    method_name = METHOD_NAMES.get(method, method)
    text = (
        f"◈ <b>Заявка на выплату создана</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Сумма: <b>{amount:.2f} ₽</b>\n"
        f"Способ: <b>{method_name}</b>\n\n"
        f"Ожидайте выплату в течение 5 минут."
    )
    await message.answer(text, reply_markup=back_to_profile_kb(), parse_mode="HTML")
    await state.clear()

    from bot.config import ADMIN_IDS
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"📨 Новая заявка на вывод #{withdrawal_id}\n"
                f"Пользователь: @{message.from_user.username or message.from_user.id}\n"
                f"Сумма: {amount:.2f} ₽\n"
                f"Способ: {method_name}\n"
                f"Реквизиты: {details}",
            )
        except Exception:
            pass
