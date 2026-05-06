from __future__ import annotations

import logging
from decimal import Decimal

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Config
from database import Database
from keyboards import (
    back_to_menu_kb,
    buy_choice_kb,
    buy_payment_kb,
    cancel_kb,
    main_menu_kb,
    order_created_user_kb,
    orders_menu_kb,
    profile_kb,
    review_rating_kb,
    review_visibility_kb,
    reviews_kb,
    support_menu_kb,
    topup_payment_kb,
)
from notification_service import notify_new_order, notify_new_topup, notify_support_ticket
from order_service import (
    orders_list_text,
    payment_method_plain,
    payment_method_public,
    payment_method_url,
    profile_text,
    referral_text,
    reviews_text,
)
from states import BuyStates, PromoStates, ReviewStates, SellStates, SupportStates, TopUpStates
from utils import fmt_gold, fmt_money, gold, h, money, parse_positive_decimal, short_text, to_decimal

router = Router(name="user")
logger = logging.getLogger(__name__)


async def ensure_user(db: Database, message_or_callback) -> object:
    user = await db.get_user_by_tg(message_or_callback.from_user.id)
    if user is None:
        user = await db.upsert_user(message_or_callback.from_user)
    return user


def render_template(text: str, *, support: str, order_id: int) -> str:
    try:
        return text.format(support=support, order_id=order_id)
    except Exception:
        return text.replace("{support}", support).replace("{order_id}", str(order_id))


def extract_start_payload(message: Message) -> str | None:
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) == 2:
        return parts[1].strip()
    return None


def menu_text(settings: dict[str, str]) -> str:
    bot_name = h(settings.get("bot_name", "VoxShop"))
    welcome = h(settings.get("welcome_text", "Добро пожаловать в VoxShop."))
    return (
        f"<b>🛒 {bot_name}</b>\n"
        "<i>Standoff 2 Gold Market</i>\n"
        "━━━━━━━━━━━━\n\n"
        f"{welcome}\n\n"
        "Выберите действие ниже:"
    )


def short_menu_text(settings: dict[str, str]) -> str:
    return (
        f"<b>🛒 {h(settings.get('bot_name', 'VoxShop'))}</b>\n"
        "━━━━━━━━━━━━\n"
        "Покупка, продажа, баланс, промокоды и отзывы."
    )


def support_contact(settings: dict[str, str], config: Config) -> str:
    return settings.get("support_contact") or config.support_contact or "@kawalskuy"


async def get_ref_link(bot: Bot, user) -> str:
    try:
        me = await bot.get_me()
        if me.username:
            return f"https://t.me/{me.username}?start=ref_{user['telegram_id']}"
    except Exception:
        logger.exception("Failed to build referral link")
    return f"/start ref_{user['telegram_id']}"


async def send_buy_payment_message(
    target: Message | CallbackQuery,
    state: FSMContext,
    *,
    balance_used: Decimal,
    payment_due: Decimal,
) -> None:
    data = await state.get_data()
    await state.update_data(balance_used=str(money(balance_used)), payment_due=str(money(payment_due)))
    await state.set_state(BuyStates.receipt)
    total = to_decimal(data["total"])
    amount = to_decimal(data["amount"])
    payment_url = data.get("payment_url")
    payment_details = data.get("payment_details_public", "DonateAlerts")

    lines = [
        "<b>💳 Оплата заказа</b>",
        "━━━━━━━━━━━━",
        "",
        f"💎 Голда:  <b>{fmt_gold(amount)}</b>",
        f"💰 Итого:  <b>{fmt_money(total)}</b>",
    ]
    if balance_used > 0:
        lines.append(f"📥 С баланса:  <b>{fmt_money(balance_used)}</b>")
    lines.append(f"💳 К оплате:  <b>{fmt_money(payment_due)}</b>")
    lines.extend(
        [
            "",
            "━━━━━━━━━━━━",
            "",
            f"<b>🏦 Способ оплаты</b>",
            payment_details,
            "",
            "━━━━━━━━━━━━",
            "",
            "Нажмите <b>«Оплатить в DonateAlerts»</b>.",
            "После оплаты отправьте чек: фото, документ или комментарий.",
        ]
    )
    text = "\n".join(lines)
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=buy_payment_kb(payment_url))
        await target.answer()
    else:
        await target.answer(text, reply_markup=buy_payment_kb(payment_url))


async def send_after_order_created(
    message: Message | CallbackQuery,
    db: Database,
    config: Config,
    *,
    order_id: int,
    order_type: str,
    status_line: str,
) -> None:
    settings = await db.get_settings()
    support = support_contact(settings, config)
    key = "after_buy_text" if order_type == "buy" else "after_sell_text"
    after_text = render_template(settings.get(key, ""), support=support, order_id=order_id)
    title = "покупка голды" if order_type == "buy" else "продажа голды"
    text = (
        f"<b>✅ Заявка #{order_id} создана</b>\n"
        "━━━━━━━━━━━━\n"
        f"Тип: <b>{title}</b>\n"
        f"Статус: <b>{status_line}</b>\n\n"
        f"{h(after_text)}"
    )
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, reply_markup=order_created_user_kb(support, order_id))
    else:
        await message.answer(text, reply_markup=order_created_user_kb(support, order_id))


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database) -> None:
    existed = await db.get_user_by_tg(message.from_user.id)
    user = await db.upsert_user(message.from_user)
    payload = extract_start_payload(message)
    if existed is None and payload and payload.startswith("ref_"):
        raw_ref = payload.replace("ref_", "", 1)
        if raw_ref.isdigit():
            await db.set_referrer_if_possible(user["id"], int(raw_ref))
            user = await db.get_user_by_tg(message.from_user.id)
    settings = await db.get_settings()
    await message.answer(menu_text(settings), reply_markup=main_menu_kb())


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    settings = await db.get_settings()
    await message.answer(short_menu_text(settings), reply_markup=main_menu_kb())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_menu_kb())


@router.callback_query(F.data == "flow:cancel")
async def cb_flow_cancel(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await state.clear()
    await callback.message.edit_text("Действие отменено. Выберите другой раздел:", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await state.clear()
    settings = await db.get_settings()
    await callback.message.edit_text(short_menu_text(settings), reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "user:profile")
async def cb_profile(callback: CallbackQuery, db: Database) -> None:
    user = await ensure_user(db, callback)
    stats = await db.get_user_order_stats(user["id"])
    await callback.message.edit_text(profile_text(user, stats), reply_markup=profile_kb())
    await callback.answer()


@router.callback_query(F.data == "user:referral")
async def cb_referral(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    user = await ensure_user(db, callback)
    stats = await db.get_user_order_stats(user["id"])
    ref_link = await get_ref_link(bot, user)
    await callback.message.edit_text(referral_text(user, stats, ref_link), reply_markup=back_to_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "faq:show")
async def cb_faq(callback: CallbackQuery, db: Database) -> None:
    faq = await db.get_setting("faq_text")
    await callback.message.edit_text(
        f"<b>📘 Правила VoxShop</b>\n━━━━━━━━━━━━\n\n{h(faq)}",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "buy:start")
async def cb_buy_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await ensure_user(db, callback)
    await state.clear()
    settings = await db.get_settings()
    text = (
        "<b>💎 Купить голду</b>\n"
        "━━━━━━━━━━━━\n"
        f"Курс: <b>{h(settings['sell_rate_to_user'])} ₽</b> за 1 голду\n"
        f"Лимиты: <b>{h(settings['min_buy_gold'])}</b>–<b>{h(settings['max_gold'])}</b> голды\n\n"
        "Введите количество голды одним числом.\n"
        "Например: <code>100</code>"
    )
    await state.set_state(BuyStates.amount)
    await callback.message.edit_text(text, reply_markup=cancel_kb())
    await callback.answer()


@router.message(BuyStates.amount)
async def msg_buy_amount(message: Message, state: FSMContext, db: Database) -> None:
    try:
        amount = parse_positive_decimal(message.text)
    except ValueError:
        await message.answer(
            "<b>Неверное количество</b>\n\nВведите только число больше нуля. Например: <code>100</code>",
            reply_markup=cancel_kb(),
        )
        return

    user = await ensure_user(db, message)
    settings = await db.get_settings()
    min_amount = to_decimal(settings["min_buy_gold"])
    max_amount = to_decimal(settings["max_gold"])
    if amount < min_amount:
        await message.answer(f"Минимум для покупки: <b>{fmt_gold(min_amount)}</b> голды.", reply_markup=cancel_kb())
        return
    if amount > max_amount:
        await message.answer(f"Максимум для одной заявки: <b>{fmt_gold(max_amount)}</b> голды.", reply_markup=cancel_kb())
        return

    methods = await db.list_payment_methods(active_only=True)
    if not methods:
        await state.clear()
        await message.answer(
            "<b>Оплата временно недоступна</b>\n\nСейчас нет активных реквизитов. Напишите в поддержку или попробуйте позже.",
            reply_markup=main_menu_kb(),
        )
        return

    method = methods[0]
    rate = to_decimal(settings["sell_rate_to_user"])
    total = money(amount * rate)
    user_balance = money(user["balance"])
    payment_url = payment_method_url(method)

    await state.update_data(
        amount=str(gold(amount)),
        rate=str(rate),
        total=str(total),
        payment_details=payment_method_plain(method),
        payment_details_public=payment_method_public(method),
        payment_url=payment_url,
    )

    if user_balance > 0:
        can_pay_balance = user_balance >= total
        can_use_partial = Decimal("0") < user_balance < total
        if can_pay_balance:
            hint = f"💰 Ваш баланс: <b>{fmt_money(user_balance)}</b> — хватает для оплаты."
        else:
            hint = f"💰 Ваш баланс: <b>{fmt_money(user_balance)}</b>\n💳 Доплата: <b>{fmt_money(total - user_balance)}</b>"
        await message.answer(
            "<b>💎 Подтверждение покупки</b>\n"
            "━━━━━━━━━━━━\n\n"
            f"💎 Голда:  <b>{fmt_gold(amount)}</b>\n"
            f"💰 К оплате:  <b>{fmt_money(total)}</b>\n\n"
            "━━━━━━━━━━━━\n\n"
            f"{hint}\n\n"
            "Выберите способ оплаты:",
            reply_markup=buy_choice_kb(can_pay_balance=can_pay_balance, can_use_partial=can_use_partial),
        )
        return

    await send_buy_payment_message(message, state, balance_used=Decimal("0"), payment_due=total)


@router.callback_query(F.data == "buy:pay_donate")
async def cb_buy_pay_donate(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    total = to_decimal(data.get("total", "0"))
    if total <= 0:
        await callback.answer("Начните покупку заново.", show_alert=True)
        return
    await send_buy_payment_message(callback, state, balance_used=Decimal("0"), payment_due=total)


@router.callback_query(F.data == "buy:pay_mixed")
async def cb_buy_pay_mixed(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    total = to_decimal(data.get("total", "0"))
    user = await ensure_user(db, callback)
    balance = money(user["balance"])
    if balance <= 0 or balance >= total:
        await callback.answer("Этот способ сейчас недоступен.", show_alert=True)
        return
    await send_buy_payment_message(callback, state, balance_used=balance, payment_due=money(total - balance))


@router.callback_query(F.data == "buy:pay_balance")
async def cb_buy_pay_balance(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot, config: Config) -> None:
    data = await state.get_data()
    user = await ensure_user(db, callback)
    total = money(data.get("total", "0"))
    balance = money(user["balance"])
    if total <= 0 or balance < total:
        await callback.answer("На балансе недостаточно средств.", show_alert=True)
        return
    try:
        order_id = await db.create_order_with_balance_deduction(
            user_id=user["id"],
            order_type="buy",
            gold_amount=data["amount"],
            rate=data["rate"],
            total_amount=data["total"],
            payment_details="Оплата балансом VoxShop",
            user_payment_details=None,
            receipt_file_id=None,
            receipt_file_type=None,
            comment="Оплачено с внутреннего баланса",
            status="paid",
            balance_used=str(total),
            payment_due="0",
        )
    except ValueError:
        await callback.answer("На балансе недостаточно средств.", show_alert=True)
        return
    await state.clear()
    await notify_new_order(bot, db, config, order_id)
    await send_after_order_created(
        callback,
        db,
        config,
        order_id=order_id,
        order_type="buy",
        status_line="оплачена балансом, ждёт выдачи",
    )
    await callback.answer("✅ Оплачено балансом.")


@router.callback_query(F.data == "buy:receipt_help")
async def cb_buy_receipt_help(callback: CallbackQuery) -> None:
    await callback.answer(
        "Отправьте чек прямо сюда: фото, документ или текстовый комментарий к оплате.",
        show_alert=True,
    )


@router.message(BuyStates.receipt)
async def msg_buy_receipt(message: Message, state: FSMContext, db: Database, bot: Bot, config: Config) -> None:
    data = await state.get_data()
    user = await ensure_user(db, message)

    receipt_file_id = None
    receipt_file_type = None
    comment = None

    if message.photo:
        receipt_file_id = message.photo[-1].file_id
        receipt_file_type = "photo"
        comment = message.caption
    elif message.document:
        receipt_file_id = message.document.file_id
        receipt_file_type = "document"
        comment = message.caption
    elif message.text:
        comment = message.text
    else:
        await message.answer("Отправьте чек фото/документом или напишите комментарий к оплате.", reply_markup=cancel_kb())
        return

    balance_used = data.get("balance_used", "0")
    payment_due = data.get("payment_due", data["total"])
    try:
        order_id = await db.create_order_with_balance_deduction(
            user_id=user["id"],
            order_type="buy",
            gold_amount=data["amount"],
            rate=data["rate"],
            total_amount=data["total"],
            payment_details=data["payment_details"],
            user_payment_details=None,
            receipt_file_id=receipt_file_id,
            receipt_file_type=receipt_file_type,
            comment=comment,
            status="waiting_payment",
            balance_used=balance_used,
            payment_due=payment_due,
        )
    except ValueError:
        await state.clear()
        await message.answer(
            "⚠️ На балансе уже недостаточно средств. Покупка отменена, начните заново.",
            reply_markup=main_menu_kb(),
        )
        return

    await state.clear()
    logger.info("Created buy order %s for user %s", order_id, message.from_user.id)
    await notify_new_order(bot, db, config, order_id, receipt_file_id=receipt_file_id, receipt_file_type=receipt_file_type)
    await send_after_order_created(message, db, config, order_id=order_id, order_type="buy", status_line="ожидает проверки оплаты")


@router.callback_query(F.data == "sell:start")
async def cb_sell_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await ensure_user(db, callback)
    await state.clear()
    settings = await db.get_settings()
    text = (
        "<b>🤝 Продать голду</b>\n"
        "━━━━━━━━━━━━\n"
        f"Курс выкупа: <b>{h(settings['buy_rate_from_user'])} ₽</b> за 1 голду\n"
        f"Лимиты: <b>{h(settings['min_sell_gold'])}</b>–<b>{h(settings['max_gold'])}</b> голды\n\n"
        "Введите количество голды, которое хотите продать.\n"
        "Например: <code>100</code>"
    )
    await state.set_state(SellStates.amount)
    await callback.message.edit_text(text, reply_markup=cancel_kb())
    await callback.answer()


@router.message(SellStates.amount)
async def msg_sell_amount(message: Message, state: FSMContext, db: Database) -> None:
    try:
        amount = parse_positive_decimal(message.text)
    except ValueError:
        await message.answer(
            "<b>Неверное количество</b>\n\nВведите только число больше нуля. Например: <code>100</code>",
            reply_markup=cancel_kb(),
        )
        return

    settings = await db.get_settings()
    min_amount = to_decimal(settings["min_sell_gold"])
    max_amount = to_decimal(settings["max_gold"])
    if amount < min_amount:
        await message.answer(f"Минимум для продажи: <b>{fmt_gold(min_amount)}</b> голды.", reply_markup=cancel_kb())
        return
    if amount > max_amount:
        await message.answer(f"Максимум для одной заявки: <b>{fmt_gold(max_amount)}</b> голды.", reply_markup=cancel_kb())
        return

    rate = to_decimal(settings["buy_rate_from_user"])
    total = money(amount * rate)

    await state.update_data(amount=str(gold(amount)), rate=str(rate), total=str(total))
    await state.set_state(SellStates.payment_details)
    await message.answer(
        "<b>🤝 Заявка на продажу</b>\n"
        "━━━━━━━━━━━━\n"
        f"Голда: <b>{fmt_gold(amount)}</b>\n"
        f"К выплате: <b>{fmt_money(total)}</b>\n\n"
        "Отправьте реквизиты для выплаты одним сообщением.\n"
        "Пример: <code>Сбер, СБП +79990000000, Иван И.</code>\n\n"
        "Не отправляйте пароли, коды и данные входа.",
        reply_markup=cancel_kb(),
    )


@router.message(SellStates.payment_details)
async def msg_sell_payment_details(message: Message, state: FSMContext, db: Database, bot: Bot, config: Config) -> None:
    details = (message.text or "").strip()
    if len(details) < 5:
        await message.answer("Укажите банк/СБП/телефон/имя получателя одним сообщением.", reply_markup=cancel_kb())
        return

    data = await state.get_data()
    user = await ensure_user(db, message)
    order_id = await db.create_order(
        user_id=user["id"],
        order_type="sell",
        gold_amount=data["amount"],
        rate=data["rate"],
        total_amount=data["total"],
        payment_details=None,
        user_payment_details=details,
        receipt_file_id=None,
        receipt_file_type=None,
        comment=None,
        status="new",
        balance_used="0",
        payment_due="0",
    )

    await state.clear()
    logger.info("Created sell order %s for user %s", order_id, message.from_user.id)
    await notify_new_order(bot, db, config, order_id)
    await send_after_order_created(message, db, config, order_id=order_id, order_type="sell", status_line="ожидает принятия администратором")


# Balance top-up
@router.callback_query(F.data == "topup:start")
async def cb_topup_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await ensure_user(db, callback)
    await state.clear()
    await state.set_state(TopUpStates.amount)
    await callback.message.edit_text(
        "<b>💰 Пополнение баланса</b>\n"
        "━━━━━━━━━━━━\n"
        "Введите сумму пополнения в рублях.\n"
        "Например: <code>500</code>\n\n"
        "После оплаты отправьте чек. Зачисление выполняется вручную администратором.",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(TopUpStates.amount)
async def msg_topup_amount(message: Message, state: FSMContext, db: Database) -> None:
    try:
        amount = money(parse_positive_decimal(message.text))
    except ValueError:
        await message.answer("Введите сумму числом. Например: <code>500</code>", reply_markup=cancel_kb())
        return
    if amount < Decimal("1"):
        await message.answer("Минимальная сумма пополнения: <b>1 ₽</b>.", reply_markup=cancel_kb())
        return
    methods = await db.list_payment_methods(active_only=True)
    if not methods:
        await state.clear()
        await message.answer("Сейчас нет активных реквизитов для оплаты.", reply_markup=main_menu_kb())
        return
    method = methods[0]
    await state.update_data(
        amount=str(amount),
        payment_details=payment_method_plain(method),
        payment_details_public=payment_method_public(method),
        payment_url=payment_method_url(method),
    )
    await state.set_state(TopUpStates.receipt)
    await message.answer(
        "<b>💳 Оплата пополнения</b>\n"
        "━━━━━━━━━━━━\n\n"
        f"💰 Сумма:  <b>{fmt_money(amount)}</b>\n\n"
        "━━━━━━━━━━━━\n\n"
        f"<b>🏦 Способ оплаты</b>\n"
        f"{payment_method_public(method)}\n\n"
        "━━━━━━━━━━━━\n\n"
        "Нажмите кнопку оплаты, затем отправьте чек.",
        reply_markup=topup_payment_kb(payment_method_url(method)),
    )


@router.callback_query(F.data == "topup:receipt_help")
async def cb_topup_receipt_help(callback: CallbackQuery) -> None:
    await callback.answer("Отправьте чек сюда: фото, документ или текстовый комментарий к оплате.", show_alert=True)


@router.message(TopUpStates.receipt)
async def msg_topup_receipt(message: Message, state: FSMContext, db: Database, bot: Bot, config: Config) -> None:
    data = await state.get_data()
    user = await ensure_user(db, message)
    receipt_file_id = None
    receipt_file_type = None
    comment = None
    if message.photo:
        receipt_file_id = message.photo[-1].file_id
        receipt_file_type = "photo"
        comment = message.caption
    elif message.document:
        receipt_file_id = message.document.file_id
        receipt_file_type = "document"
        comment = message.caption
    elif message.text:
        comment = message.text
    else:
        await message.answer("Отправьте чек фото/документом или напишите комментарий к оплате.", reply_markup=cancel_kb())
        return

    topup_id = await db.create_topup(
        user_id=user["id"],
        amount=data["amount"],
        payment_details=data.get("payment_details"),
        receipt_file_id=receipt_file_id,
        receipt_file_type=receipt_file_type,
        comment=comment,
    )
    await state.clear()
    await notify_new_topup(bot, db, config, topup_id, receipt_file_id=receipt_file_id, receipt_file_type=receipt_file_type)
    await message.answer(
        f"<b>✅ Пополнение #{topup_id} создано</b>\n"
        "━━━━━━━━━━━━\n"
        f"Сумма: <b>{fmt_money(data['amount'])}</b>\n"
        "Статус: <b>ожидает проверки</b>\n\n"
        "После подтверждения администратором деньги появятся на балансе.",
        reply_markup=profile_kb(),
    )


# Promo codes
@router.callback_query(F.data == "promo:start")
async def cb_promo_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await ensure_user(db, callback)
    await state.clear()
    await state.set_state(PromoStates.code)
    await callback.message.edit_text(
        "<b>🎁 Активация промокода</b>\n"
        "━━━━━━━━━━━━\n"
        "Отправьте промокод одним сообщением.\n"
        "После успешной активации сумма добавится на баланс.",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(PromoStates.code)
async def msg_promo_code(message: Message, state: FSMContext, db: Database) -> None:
    user = await ensure_user(db, message)
    code = (message.text or "").strip()
    result = await db.activate_promo(user["id"], code)
    if not result["ok"]:
        reason = result.get("reason")
        text_by_reason = {
            "not_found": "Промокод не найден.",
            "inactive": "Промокод выключен.",
            "limit": "Лимит активаций промокода закончился.",
            "already": "Вы уже активировали этот промокод.",
            "empty": "Введите промокод текстом.",
        }
        await message.answer(f"⚠️ {text_by_reason.get(reason, 'Не удалось активировать промокод.')}", reply_markup=profile_kb())
        await state.clear()
        return
    await state.clear()
    await message.answer(
        "<b>🎁 Промокод активирован</b>\n"
        "━━━━━━━━━━━━\n"
        f"Код: <code>{h(result['code'])}</code>\n"
        f"Начислено: <b>{fmt_money(result['amount'])}</b>\n"
        f"Новый баланс: <b>{fmt_money(result['new_balance'])}</b>",
        reply_markup=profile_kb(),
    )


# Reviews
@router.callback_query(F.data == "reviews:show")
async def cb_reviews_show(callback: CallbackQuery, db: Database) -> None:
    total = await db.get_reviews_count()
    avg_rating = await db.get_average_rating()
    reviews = await db.list_recent_reviews(5)
    await callback.message.edit_text(reviews_text(total, reviews, avg_rating), reply_markup=reviews_kb())
    await callback.answer()


@router.callback_query(F.data == "review:general")
async def cb_review_general(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await ensure_user(db, callback)
    await state.clear()
    await state.set_state(ReviewStates.rating)
    await state.update_data(order_id=None)
    await callback.message.edit_text(
        "<b>⭐ Новый отзыв</b>\n"
        "━━━━━━━━━━━━\n\n"
        "Выберите оценку от 1 до 5 звёзд:",
        reply_markup=review_rating_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("review:start:"))
async def cb_review_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    user = await ensure_user(db, callback)
    order_id = int(callback.data.split(":")[2])

    if order_id <= 0:
        await callback.answer(
            "Отзыв можно оставить только после завершённой покупки или продажи.",
            show_alert=True,
        )
        return

    order = await db.get_order_with_user(order_id)
    if order is None or int(order["telegram_id"]) != int(callback.from_user.id):
        await callback.answer("Заявка не найдена.", show_alert=True)
        return
    if order["status"] != "completed":
        await callback.answer("Отзыв можно оставить после завершения заявки.", show_alert=True)
        return
    if await db.has_review_for_order(user["id"], order_id):
        await callback.answer("Вы уже оставляли отзыв по этой заявке.", show_alert=True)
        return

    await state.clear()
    await state.set_state(ReviewStates.rating)
    await state.update_data(order_id=order_id)
    await callback.message.edit_text(
        "<b>⭐ Новый отзыв</b>\n"
        "━━━━━━━━━━━━\n\n"
        "Выберите оценку от 1 до 5 звёзд:",
        reply_markup=review_rating_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("review:rating:"))
async def cb_review_rating(callback: CallbackQuery, state: FSMContext) -> None:
    rating = int(callback.data.split(":")[2])
    await state.update_data(rating=rating)
    await state.set_state(ReviewStates.visibility)
    await callback.message.edit_text(
        "<b>⭐ Отзыв</b>\n"
        "━━━━━━━━━━━━\n"
        f"Оценка: <b>{'⭐' * rating}</b>\n\n"
        "Как показать отзыв?",
        reply_markup=review_visibility_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("review:visibility:"))
async def cb_review_visibility(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(is_anonymous=(value == "anon"))
    await state.set_state(ReviewStates.text)
    await callback.message.edit_text(
        "<b>📝 Текст отзыва</b>\n"
        "━━━━━━━━━━━━\n"
        "Напишите отзыв одним сообщением.\n"
        "Например: <code>Всё быстро, голду получил.</code>",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(ReviewStates.text)
async def msg_review_text(message: Message, state: FSMContext, db: Database) -> None:
    text = (message.text or "").strip()
    if len(text) < 3:
        await message.answer("Отзыв слишком короткий. Напишите пару слов.", reply_markup=cancel_kb())
        return
    if len(text) > 700:
        text = short_text(text, 700)
    data = await state.get_data()
    user = await ensure_user(db, message)
    is_anonymous = bool(data.get("is_anonymous", True))
    display_name = "Аноним" if is_anonymous else (f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name or "Клиент")
    review_id = await db.create_review(
        user_id=user["id"],
        order_id=data.get("order_id"),
        rating=int(data.get("rating", 5)),
        text=text,
        is_anonymous=is_anonymous,
        display_name=display_name,
    )
    await state.clear()
    await message.answer(
        f"<b>✅ Отзыв #{review_id} опубликован</b>\n\nСпасибо, что помогаете VoxShop становиться лучше.",
        reply_markup=reviews_kb(),
    )


@router.callback_query(F.data == "orders:menu")
async def cb_orders_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text("<b>📦 Мои заявки</b>\n━━━━━━━━━━━━\n\nВыберите список заявок:", reply_markup=orders_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("orders:"))
async def cb_orders_list(callback: CallbackQuery, db: Database) -> None:
    category = callback.data.split(":", 1)[1]
    if category == "menu":
        await callback.answer()
        return
    user = await ensure_user(db, callback)
    orders = await db.list_user_orders(user["id"], category)
    title = {
        "active": "🟡 Активные заявки",
        "completed": "✅ Завершённые заявки",
        "rejected": "⛔ Отклонённые заявки",
    }.get(category, "📦 Мои заявки")
    await callback.message.edit_text(orders_list_text(title, orders), reply_markup=orders_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "support:start")
async def cb_support_start(callback: CallbackQuery, db: Database, config: Config) -> None:
    settings = await db.get_settings()
    support = support_contact(settings, config)
    await callback.message.edit_text(
        "<b>💬 Поддержка VoxShop</b>\n"
        "━━━━━━━━━━━━\n"
        f"Основной контакт: <b>{h(support)}</b>\n\n"
        "По вопросам покупки, продажи, выдачи голды и выплат лучше писать напрямую. Также можно создать обращение внутри бота.",
        reply_markup=support_menu_kb(support),
    )
    await callback.answer()


@router.callback_query(F.data == "support:create")
async def cb_support_create(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SupportStates.message)
    await callback.message.edit_text(
        "<b>📝 Новое обращение</b>\n"
        "━━━━━━━━━━━━\n"
        "Опишите вопрос одним сообщением. Если вопрос связан со сделкой, укажите номер заявки.",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(SupportStates.message)
async def msg_support(message: Message, state: FSMContext, db: Database, bot: Bot, config: Config) -> None:
    text = (message.text or "").strip()
    if len(text) < 3:
        await message.answer("Опишите вопрос подробнее, чтобы администратор понял ситуацию.", reply_markup=cancel_kb())
        return

    user = await ensure_user(db, message)
    ticket_id = await db.create_support_ticket(user["id"], text)
    await state.clear()
    await notify_support_ticket(bot, db, config, ticket_id)
    await message.answer(
        f"<b>✅ Обращение #{ticket_id} отправлено</b>\n\nАдминистратор получит уведомление и ответит через бота.",
        reply_markup=main_menu_kb(),
    )
