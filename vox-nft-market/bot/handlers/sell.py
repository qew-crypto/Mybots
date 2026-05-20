import asyncio
import logging

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.database import (
    is_banned, get_deal_by_nft_link, create_deal, get_deal,
    update_deal_status, update_balance, add_log, get_user,
    get_setting,
)
from bot.services.nft import parse_nft_link, get_nft_info, check_nft_owner, get_gift_price_ton
from bot.services.currency import ton_to_rub
from bot.keyboards import sell_cancel_kb, deal_actions_kb, deal_confirmed_kb, main_menu_kb
from bot.config import NFT_RECEIVER_USERNAME, EVALUATION_PERCENT, CHECK_INTERVAL_SECONDS, CHECK_TIMEOUT_SECONDS, ADMIN_IDS

router = Router()
logger = logging.getLogger(__name__)


class SellStates(StatesGroup):
    waiting_nft_link = State()


SELL_PROMPT = (
    "◈ <b>Продажа NFT</b>\n"
    "━━━━━━━━━━━━━━━━━━━\n\n"
    "Отправьте ссылку на NFT-подарок,\n"
    "который хотите продать.\n\n"
    "Формат: <code>t.me/nft/Name-12345</code>"
)


@router.message(Command("sell"))
async def cmd_sell(message: Message, state: FSMContext):
    if await is_banned(message.from_user.id):
        await message.answer("⛔ Ваш аккаунт ограничен.")
        return
    await state.set_state(SellStates.waiting_nft_link)
    await message.answer(SELL_PROMPT, reply_markup=sell_cancel_kb(), parse_mode="HTML")


@router.callback_query(F.data == "sell_nft")
async def cb_sell_nft(callback: CallbackQuery, state: FSMContext):
    if await is_banned(callback.from_user.id):
        await callback.answer("⛔ Ваш аккаунт ограничен.", show_alert=True)
        return

    await state.set_state(SellStates.waiting_nft_link)
    await callback.message.edit_text(SELL_PROMPT, reply_markup=sell_cancel_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "cancel_sell")
async def cb_cancel_sell(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    from bot.handlers.start import WELCOME_TEXT
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.message(SellStates.waiting_nft_link)
async def process_nft_link(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id

    if await is_banned(user_id):
        await message.answer("⛔ Ваш аккаунт ограничен.")
        await state.clear()
        return

    slug = parse_nft_link(message.text or "")
    if not slug:
        await message.answer(
            "❌ Не удалось распознать ссылку.\n"
            "Отправьте ссылку в формате: <code>t.me/nft/Name-12345</code>",
            parse_mode="HTML",
        )
        return

    nft_link = f"t.me/nft/{slug}"

    existing = await get_deal_by_nft_link(nft_link)
    if existing:
        await message.answer("⚠️ Этот NFT уже участвовал в сделке.")
        return

    processing_msg = await message.answer("🔍 Анализирую NFT...")

    nft_data = await get_nft_info(slug)
    if not nft_data:
        await processing_msg.edit_text(
            "❌ NFT не найден или ссылка недоступна.\n"
            "Проверьте ссылку и попробуйте снова.",
        )
        return

    eval_percent = float(await get_setting("eval_percent", str(EVALUATION_PERCENT)))
    receiver = await get_setting("nft_receiver", NFT_RECEIVER_USERNAME)

    price_ton = await get_gift_price_ton(slug)
    if price_ton is None:
        price_ton = 0.5

    price_rub_full = await ton_to_rub(price_ton)
    if price_rub_full is None:
        await processing_msg.edit_text("⏳ Оценка временно недоступна. Попробуйте чуть позже.")
        return

    price_rub = round(price_rub_full * (eval_percent / 100), 2)

    model = nft_data.get("model", nft_data.get("collection", slug))
    collection = nft_data.get("collection", "—")
    rarity = nft_data.get("rarity", "—")
    owner = nft_data.get("owner", "")

    deal_id = await create_deal(
        user_id=user_id,
        nft_link=nft_link,
        nft_name=model,
        collection=collection,
        rarity=rarity,
        price_ton=price_ton,
        price_rub=price_rub,
        owner_before=owner,
    )

    await add_log(user_id, "nft_evaluated", f"Deal #{deal_id} | {nft_link} | {price_rub} ₽")

    offer_text = (
        f"◈ <b>NFT найден</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Модель: <b>{model}</b>\n"
        f"Коллекция: <b>{collection}</b>\n"
        f"Редкость: <b>{rarity}</b>\n\n"
        f"💰 Оценка: <b>{price_rub} ₽</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Для продажи передайте NFT на аккаунт:\n"
        f"<b>@{receiver}</b>\n\n"
        f"После передачи бот автоматически\n"
        f"проверит смену владельца и начислит\n"
        f"средства на ваш баланс."
    )

    await processing_msg.edit_text(offer_text, reply_markup=deal_actions_kb(deal_id), parse_mode="HTML")
    await state.clear()

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"📥 Новая сделка #{deal_id}\n"
                f"Пользователь: {message.from_user.username or user_id}\n"
                f"NFT: {nft_link}\n"
                f"Сумма: {price_rub} ₽",
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("check_transfer:"))
async def cb_check_transfer(callback: CallbackQuery, bot: Bot):
    deal_id = int(callback.data.split(":")[1])
    deal = await get_deal(deal_id)

    if not deal:
        await callback.answer("Сделка не найдена.", show_alert=True)
        return

    if deal["user_id"] != callback.from_user.id:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    if deal["status"] not in ("awaiting_transfer", "checking"):
        await callback.answer("Сделка уже обработана.", show_alert=True)
        return

    await update_deal_status(deal_id, "checking")
    await callback.answer("🔄 Проверяю передачу...")

    slug = deal["nft_link"].replace("t.me/nft/", "")
    receiver = await get_setting("nft_receiver", NFT_RECEIVER_USERNAME)

    current_owner = await check_nft_owner(slug)

    if current_owner and current_owner.lower().strip("@") == receiver.lower():
        await update_deal_status(deal_id, "completed")
        await update_balance(deal["user_id"], deal["price_rub"])
        await add_log(deal["user_id"], "deal_completed", f"Deal #{deal_id} | +{deal['price_rub']} ₽")

        confirmed_text = (
            f"◈ <b>Передача подтверждена</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"На ваш баланс начислено: <b>{deal['price_rub']} ₽</b>"
        )
        await callback.message.edit_text(
            confirmed_text, reply_markup=deal_confirmed_kb(), parse_mode="HTML"
        )

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"✅ Сделка #{deal_id} подтверждена\n"
                    f"Баланс начислен: {deal['price_rub']} ₽",
                )
            except Exception:
                pass
    else:
        await update_deal_status(deal_id, "awaiting_transfer")
        await callback.message.edit_text(
            "⏳ Передача пока не найдена.\n\n"
            f"Убедитесь, что NFT отправлен на <b>@{receiver}</b>.",
            reply_markup=deal_actions_kb(deal_id),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("cancel_deal:"))
async def cb_cancel_deal(callback: CallbackQuery):
    deal_id = int(callback.data.split(":")[1])
    deal = await get_deal(deal_id)

    if not deal:
        await callback.answer("Сделка не найдена.", show_alert=True)
        return

    if deal["user_id"] != callback.from_user.id:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    if deal["status"] in ("completed",):
        await callback.answer("Сделка уже завершена.", show_alert=True)
        return

    await update_deal_status(deal_id, "cancelled")
    await add_log(deal["user_id"], "deal_cancelled", f"Deal #{deal_id}")

    await callback.message.edit_text(
        "❌ Сделка отменена.",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()
