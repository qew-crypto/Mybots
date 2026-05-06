from __future__ import annotations

import logging
import sqlite3
from decimal import Decimal, InvalidOperation

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Config
from database import Database
from keyboards import (
    admin_back_kb,
    admin_bot_control_kb,
    admin_menu_kb,
    admin_review_detail_kb,
    admin_review_rating_kb,
    admin_reviews_list_kb,
    admin_reviews_menu_kb,
    admin_order_actions_kb,
    admin_orders_list_kb,
    admin_orders_menu_kb,
    admin_promos_list_kb,
    admin_promos_menu_kb,
    admin_statuses_kb,
    admin_topup_actions_kb,
    admin_topups_list_kb,
    admin_topups_menu_kb,
    mailing_confirm_kb,
    payment_detail_kb,
    payments_list_kb,
    promo_detail_kb,
    settings_kb,
    support_ticket_admin_kb,
    support_tickets_list_kb,
    user_admin_actions_kb,
    users_menu_kb,
    users_search_results_kb,
)
from mailing_service import run_mailing
from models import NUMERIC_SETTINGS, SETTING_HINTS, SETTING_TITLES
from notification_service import notify_order_status, send_to_admins
from order_service import (
    admin_review_detail_text,
    admin_reviews_text,
    admin_user_text,
    bot_control_text,
    order_admin_text,
    orders_list_text,
    payment_method_admin_text,
    payment_methods_text,
    promo_detail_text,
    promos_list_text,
    settings_text,
    stats_text,
    support_ticket_text,
    support_tickets_text,
    topup_admin_text,
    topups_list_text,
)
from states import (
    AdminBotControlStates,
    AdminDirectMessageStates,
    AdminMailingStates,
    AdminOrderStates,
    AdminPaymentStates,
    AdminPromoStates,
    AdminReviewStates,
    AdminSearchOrderStates,
    AdminSettingsStates,
    AdminSupportStates,
    AdminUserStates,
)
from utils import fmt_money, h, money, parse_positive_decimal, short_text

router = Router(name="admin")
logger = logging.getLogger(__name__)

PAYMENT_FIELD_TITLES = {
    "title": "Название реквизитов",
    "bank_name": "Описание",
    "card_number": "Ссылка / карта",
    "phone_number": "СБП / телефон",
    "recipient_name": "Имя получателя",
    "comment": "Комментарий к оплате",
}


async def is_admin(db: Database, config: Config, telegram_id: int) -> bool:
    if telegram_id in config.admin_ids:
        return True
    return await db.is_admin(telegram_id)


async def require_admin(event: Message | CallbackQuery, db: Database, config: Config) -> bool:
    ok = await is_admin(db, config, event.from_user.id)
    if ok:
        return True
    if isinstance(event, CallbackQuery):
        await event.answer("⛔ Нет доступа к админ-панели.", show_alert=True)
    else:
        await event.answer("⛔ Нет доступа к админ-панели.")
    return False


def clean_optional(text: str | None) -> str | None:
    if text is None:
        return None
    value = text.strip()
    if value in {"", "-", "нет", "Нет", "НЕТ"}:
        return None
    return value


def admin_menu_text() -> str:
    return (
        "<b>🛡 Админ-панель VoxShop</b>\n"
        "━━━━━━━━━━━━\n"
        "Заявки, баланс, промокоды, реквизиты, клиенты, поддержка и рассылки."
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    await state.clear()
    if not await require_admin(message, db, config):
        return
    await db.upsert_user(message.from_user)
    await message.answer(admin_menu_text(), reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:menu")
async def cb_admin_menu(callback: CallbackQuery, db: Database, config: Config, state: FSMContext) -> None:
    await state.clear()
    if not await require_admin(callback, db, config):
        return
    await callback.message.edit_text(admin_menu_text(), reply_markup=admin_menu_kb())
    await callback.answer()


# Orders
@router.callback_query(F.data == "admin:orders")
async def cb_admin_orders(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    await callback.message.edit_text("<b>📦 Заявки VoxShop</b>\n━━━━━━━━━━━━\n\nВыберите категорию:", reply_markup=admin_orders_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("adm_orders:"))
async def cb_admin_orders_list(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    category = callback.data.split(":", 1)[1]
    orders = await db.list_orders(category, limit=12)
    title = {
        "new": "🆕 Новые заявки",
        "active": "🟡 Заявки в работе",
        "completed": "✅ Завершённые заявки",
        "rejected": "⛔ Отклонённые / отменённые",
        "all": "📚 Все заявки",
    }.get(category, "📦 Заявки")
    await callback.message.edit_text(orders_list_text(title, orders), reply_markup=admin_orders_list_kb(orders, category))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:order:"))
async def cb_admin_order_detail(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    order_id = int(callback.data.split(":")[2])
    order = await db.get_order_with_user(order_id)
    if order is None:
        await callback.answer("⚠️ Заявка не найдена.", show_alert=True)
        return
    await callback.message.edit_text(order_admin_text(order), reply_markup=admin_order_actions_kb(order_id, order["order_type"]))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:chstatus:"))
async def cb_admin_change_status(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    order_id = int(callback.data.split(":")[2])
    await callback.message.edit_text(f"<b>🔁 Смена статуса #{order_id}</b>\n\nВыберите новый статус:", reply_markup=admin_statuses_kb(order_id))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:setstatus:"))
async def cb_admin_set_status(callback: CallbackQuery, db: Database, config: Config, bot: Bot) -> None:
    if not await require_admin(callback, db, config):
        return
    _, _, raw_order_id, status = callback.data.split(":", 3)
    order_id = int(raw_order_id)
    order = await db.get_order(order_id)
    if order is None:
        await callback.answer("⚠️ Заявка не найдена.", show_alert=True)
        return

    await db.update_order_status(order_id, status)
    await notify_order_status(bot, db, order_id, status)
    logger.info("Admin %s changed order %s status to %s", callback.from_user.id, order_id, status)

    updated = await db.get_order_with_user(order_id)
    await callback.message.edit_text(order_admin_text(updated), reply_markup=admin_order_actions_kb(order_id, updated["order_type"]))
    await callback.answer("✅ Статус обновлён.")


@router.callback_query(F.data.startswith("adm:msg:"))
async def cb_admin_message_user(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    order_id = int(callback.data.split(":")[2])
    order = await db.get_order(order_id)
    if order is None:
        await callback.answer("⚠️ Заявка не найдена.", show_alert=True)
        return
    await state.set_state(AdminOrderStates.message_user)
    await state.update_data(order_id=order_id)
    await callback.message.edit_text(f"<b>💬 Сообщение клиенту</b>\n\nЗаявка #{order_id}. Напишите текст, который нужно отправить клиенту.", reply_markup=admin_back_kb())
    await callback.answer()


@router.message(AdminOrderStates.message_user)
async def msg_admin_message_user(message: Message, state: FSMContext, db: Database, config: Config, bot: Bot) -> None:
    if not await require_admin(message, db, config):
        return
    data = await state.get_data()
    order_id = int(data["order_id"])
    order = await db.get_order_with_user(order_id)
    if order is None:
        await state.clear()
        await message.answer("⚠️ Заявка не найдена.", reply_markup=admin_menu_kb())
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer("⚠️ Введите текст сообщения.")
        return
    await bot.send_message(order["telegram_id"], f"<b>💬 Сообщение от VoxShop</b>\n\nЗаявка #{order_id}\n\n{h(text)}")
    await state.clear()
    await message.answer("✅ Сообщение отправлено клиенту.", reply_markup=admin_menu_kb())


# Settings
@router.callback_query(F.data.in_({"admin:settings", "admin:settings_rates"}))
async def cb_admin_settings_rates(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    settings = await db.get_settings()
    await callback.message.edit_text(settings_text(settings, "rates"), reply_markup=settings_kb("rates"))
    await callback.answer()


@router.callback_query(F.data == "admin:settings_texts")
async def cb_admin_settings_texts(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    settings = await db.get_settings()
    await callback.message.edit_text(settings_text(settings, "texts"), reply_markup=settings_kb("texts"))
    await callback.answer()


@router.callback_query(F.data.startswith("settings:set:"))
async def cb_admin_setting_set(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    key = callback.data.split(":", 2)[2]
    current = await db.get_setting(key)
    section = "rates" if key in NUMERIC_SETTINGS else "texts"
    await state.set_state(AdminSettingsStates.set_value)
    await state.update_data(setting_key=key, section=section)
    await callback.message.edit_text(
        f"<b>✏️ Изменить: {h(SETTING_TITLES.get(key, key))}</b>\n\n"
        f"<b>Сейчас:</b>\n<code>{h(short_text(current, 700))}</code>\n\n"
        f"<b>Подсказка:</b> {h(SETTING_HINTS.get(key, 'Введите новое значение.'))}\n\n"
        "Отправьте новое значение одним сообщением.",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminSettingsStates.set_value)
async def msg_admin_setting_value(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    data = await state.get_data()
    key = data["setting_key"]
    section = data.get("section", "rates")
    value = (message.text or "").strip()

    if key in NUMERIC_SETTINGS:
        value = value.replace(",", ".")
        try:
            parse_positive_decimal(value)
        except ValueError:
            await message.answer("⚠️ Введите положительное число. Пример: 0.85 или 100.")
            return
    else:
        if len(value) < 2:
            await message.answer("⚠️ Значение слишком короткое.")
            return
        if key == "support_contact" and not value.startswith("@"):
            await message.answer("⚠️ Контакт поддержки должен начинаться с @. Пример: @kawalskuy")
            return

    await db.set_setting(key, value)
    await state.clear()
    settings = await db.get_settings()
    await message.answer(f"✅ Настройка обновлена: <code>{h(key)}</code>\n\n{settings_text(settings, section)}", reply_markup=settings_kb(section))


# Payments
@router.callback_query(F.data == "admin:payments")
async def cb_admin_payments(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    methods = await db.list_payment_methods(active_only=False)
    await callback.message.edit_text(payment_methods_text(methods), reply_markup=payments_list_kb(methods))
    await callback.answer()


@router.callback_query(F.data == "pay:add")
async def cb_payment_add(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    await state.set_state(AdminPaymentStates.title)
    await callback.message.edit_text("<b>➕ Новые реквизиты</b>\n\nВведите название.\nПример: <code>DonateAlerts</code>", reply_markup=admin_back_kb())
    await callback.answer()


@router.message(AdminPaymentStates.title)
async def msg_payment_title(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    value = (message.text or "").strip()
    if len(value) < 2:
        await message.answer("⚠️ Название слишком короткое.")
        return
    await state.update_data(title=value)
    await state.set_state(AdminPaymentStates.bank_name)
    await message.answer("🏦 Введите описание способа оплаты. Например: Все карты + зарубеж. Если поле не нужно — отправьте <code>-</code>.")


@router.message(AdminPaymentStates.bank_name)
async def msg_payment_bank(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    await state.update_data(bank_name=clean_optional(message.text))
    await state.set_state(AdminPaymentStates.card_number)
    await message.answer("💳 Введите ссылку оплаты или номер карты/счёта. Если поле не нужно — отправьте <code>-</code>.")


@router.message(AdminPaymentStates.card_number)
async def msg_payment_card(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    await state.update_data(card_number=clean_optional(message.text))
    await state.set_state(AdminPaymentStates.phone_number)
    await message.answer("📱 Введите телефон/СБП. Если поле не нужно — отправьте <code>-</code>.")


@router.message(AdminPaymentStates.phone_number)
async def msg_payment_phone(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    await state.update_data(phone_number=clean_optional(message.text))
    await state.set_state(AdminPaymentStates.recipient_name)
    await message.answer("👤 Введите имя получателя. Если поле не нужно — отправьте <code>-</code>.")


@router.message(AdminPaymentStates.recipient_name)
async def msg_payment_recipient(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    await state.update_data(recipient_name=clean_optional(message.text))
    await state.set_state(AdminPaymentStates.comment)
    await message.answer("💬 Введите комментарий к оплате. Если комментарий не нужен — отправьте <code>-</code>.")


@router.message(AdminPaymentStates.comment)
async def msg_payment_comment(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    data = await state.get_data()
    method_id = await db.add_payment_method(
        title=data["title"],
        bank_name=data.get("bank_name"),
        card_number=data.get("card_number"),
        phone_number=data.get("phone_number"),
        recipient_name=data.get("recipient_name"),
        comment=clean_optional(message.text),
    )
    await state.clear()
    method = await db.get_payment_method(method_id)
    await message.answer(f"✅ Реквизиты #{method_id} добавлены.\n\n{payment_method_admin_text(method)}", reply_markup=payment_detail_kb(method_id, bool(method["is_active"])))


@router.callback_query(F.data.startswith("pay:view:"))
async def cb_payment_view(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    method_id = int(callback.data.split(":")[2])
    method = await db.get_payment_method(method_id)
    if method is None:
        await callback.answer("⚠️ Реквизиты не найдены.", show_alert=True)
        return
    await callback.message.edit_text(payment_method_admin_text(method), reply_markup=payment_detail_kb(method_id, bool(method["is_active"])))
    await callback.answer()


@router.callback_query(F.data.startswith("pay:toggle:"))
async def cb_payment_toggle(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    method_id = int(callback.data.split(":")[2])
    await db.toggle_payment_method(method_id)
    method = await db.get_payment_method(method_id)
    if method is None:
        await callback.answer("⚠️ Реквизиты не найдены.", show_alert=True)
        return
    await callback.message.edit_text(payment_method_admin_text(method), reply_markup=payment_detail_kb(method_id, bool(method["is_active"])))
    await callback.answer("✅ Готово.")


@router.callback_query(F.data.startswith("pay:edit:"))
async def cb_payment_edit(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    _, _, raw_method_id, field = callback.data.split(":", 3)
    method_id = int(raw_method_id)
    method = await db.get_payment_method(method_id)
    if method is None:
        await callback.answer("⚠️ Реквизиты не найдены.", show_alert=True)
        return
    await state.set_state(AdminPaymentStates.edit_value)
    await state.update_data(method_id=method_id, field=field)
    current = method[field] or "-"
    await callback.message.edit_text(
        f"<b>✏️ Изменить: {h(PAYMENT_FIELD_TITLES.get(field, field))}</b>\n\n"
        f"<b>Сейчас:</b>\n<code>{h(current)}</code>\n\n"
        "Отправьте новое значение. Чтобы очистить поле — отправьте <code>-</code>.",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminPaymentStates.edit_value)
async def msg_payment_edit_value(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    data = await state.get_data()
    method_id = int(data["method_id"])
    field = data["field"]
    value = (message.text or "").strip()
    if field == "title":
        if len(value) < 2:
            await message.answer("⚠️ Название слишком короткое.")
            return
        cleaned = value
    else:
        cleaned = clean_optional(value)
    await db.update_payment_method_field(method_id, field, cleaned)
    await state.clear()
    method = await db.get_payment_method(method_id)
    await message.answer("✅ Реквизиты обновлены.\n\n" + payment_method_admin_text(method), reply_markup=payment_detail_kb(method_id, bool(method["is_active"])))


@router.callback_query(F.data.startswith("pay:delete:"))
async def cb_payment_delete(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    method_id = int(callback.data.split(":")[2])
    await db.delete_payment_method(method_id)
    methods = await db.list_payment_methods(active_only=False)
    await callback.message.edit_text(payment_methods_text(methods), reply_markup=payments_list_kb(methods))
    await callback.answer("🗑 Удалено.")


# Top-ups
@router.callback_query(F.data == "admin:topups")
async def cb_admin_topups(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    await callback.message.edit_text("<b>💳 Пополнения баланса</b>\n━━━━━━━━━━━━\n\nВыберите категорию:", reply_markup=admin_topups_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("adm_topups:"))
async def cb_admin_topups_list(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    category = callback.data.split(":", 1)[1]
    topups = await db.list_topups(category, limit=12)
    title = {
        "waiting_payment": "🟡 Пополнения на проверке",
        "completed": "✅ Зачисленные пополнения",
        "rejected": "⛔ Отклонённые пополнения",
        "all": "📚 Все пополнения",
    }.get(category, "💳 Пополнения")
    await callback.message.edit_text(topups_list_text(title, topups), reply_markup=admin_topups_list_kb(topups, category))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:topup:"))
async def cb_admin_topup_detail(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    topup_id = int(callback.data.split(":")[2])
    topup = await db.get_topup_with_user(topup_id)
    if topup is None:
        await callback.answer("⚠️ Пополнение не найдено.", show_alert=True)
        return
    await callback.message.edit_text(topup_admin_text(topup), reply_markup=admin_topup_actions_kb(topup_id, topup["status"]))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:topupstatus:"))
async def cb_admin_topup_status(callback: CallbackQuery, db: Database, config: Config, bot: Bot) -> None:
    if not await require_admin(callback, db, config):
        return
    _, _, raw_topup_id, status = callback.data.split(":", 3)
    topup_id = int(raw_topup_id)
    old = await db.get_topup_with_user(topup_id)
    if old is None:
        await callback.answer("⚠️ Пополнение не найдено.", show_alert=True)
        return
    if status == "completed":
        result = await db.confirm_topup(topup_id)
        if not result.get("ok"):
            await callback.answer("Не удалось зачислить: статус уже изменён.", show_alert=True)
            return
        await bot.send_message(
            result["telegram_id"],
            "<b>✅ Баланс пополнен</b>\n"
            "━━━━━━━━━━━━\n"
            f"Зачислено: <b>{fmt_money(result['amount'])}</b>\n"
            f"Новый баланс: <b>{fmt_money(result['new_balance'])}</b>",
        )
        if result.get("referrer_tg") and Decimal(str(result.get("bonus", "0"))) > 0:
            try:
                await bot.send_message(
                    result["referrer_tg"],
                    "<b>🎁 Реферальный бонус</b>\n"
                    "━━━━━━━━━━━━\n"
                    f"Ваш реферал пополнил баланс. Начислено: <b>{fmt_money(result['bonus'])}</b>",
                )
            except Exception:
                logger.exception("Failed to notify referrer")
        await callback.answer("✅ Баланс зачислен.")
    elif status == "rejected":
        await db.reject_topup(topup_id)
        await bot.send_message(
            old["telegram_id"],
            f"<b>⛔ Пополнение #{topup_id} отклонено</b>\n\nЕсли есть вопрос, напишите в поддержку.",
        )
        await callback.answer("⛔ Отклонено.")
    updated = await db.get_topup_with_user(topup_id)
    await callback.message.edit_text(topup_admin_text(updated), reply_markup=admin_topup_actions_kb(topup_id, updated["status"]))


# Promo codes
@router.callback_query(F.data == "admin:promos")
async def cb_admin_promos(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    await callback.message.edit_text(
        "<b>🎁 Промокоды VoxShop</b>\n"
        "━━━━━━━━━━━━\n"
        "Создавайте одноразовые уникальные коды или обычные коды с лимитом активаций.",
        reply_markup=admin_promos_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "promo_admin:create_unique")
async def cb_promo_unique(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    await state.set_state(AdminPromoStates.unique_amount)
    await callback.message.edit_text(
        "<b>🎲 Уникальный промокод</b>\n\nВведите сумму в рублях. Бот сам создаст случайный одноразовый код.",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminPromoStates.unique_amount)
async def msg_promo_unique_amount(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    try:
        amount = money(parse_positive_decimal(message.text))
    except ValueError:
        await message.answer("⚠️ Введите сумму числом. Например: 100")
        return
    code = await db.generate_unique_promo_code()
    promo_id = await db.create_promo(code=code, amount=str(amount), max_activations=1, is_unique=True)
    await state.clear()
    promo = await db.get_promo(promo_id)
    await message.answer("✅ Уникальный промокод создан.\n\n" + promo_detail_text(promo), reply_markup=promo_detail_kb(promo_id, True))


@router.callback_query(F.data == "promo_admin:create_regular")
async def cb_promo_regular(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    await state.set_state(AdminPromoStates.regular_code)
    await callback.message.edit_text(
        "<b>✍️ Обычный промокод</b>\n\nВведите код, который будут вводить клиенты.\nПример: <code>VOX100</code>",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminPromoStates.regular_code)
async def msg_promo_regular_code(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    code = "".join((message.text or "").upper().split())
    if len(code) < 3 or len(code) > 32:
        await message.answer("⚠️ Код должен быть от 3 до 32 символов.")
        return
    await state.update_data(code=code)
    await state.set_state(AdminPromoStates.regular_amount)
    await message.answer("💰 Введите сумму начисления в рублях. Например: <code>50</code>")


@router.message(AdminPromoStates.regular_amount)
async def msg_promo_regular_amount(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    try:
        amount = money(parse_positive_decimal(message.text))
    except ValueError:
        await message.answer("⚠️ Введите сумму числом. Например: 50")
        return
    await state.update_data(amount=str(amount))
    await state.set_state(AdminPromoStates.regular_limit)
    await message.answer("🔢 Введите количество активаций. Например: <code>100</code>")


@router.message(AdminPromoStates.regular_limit)
async def msg_promo_regular_limit(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("⚠️ Введите положительное целое число.")
        return
    data = await state.get_data()
    try:
        promo_id = await db.create_promo(code=data["code"], amount=data["amount"], max_activations=int(raw), is_unique=False)
    except sqlite3.IntegrityError:
        await message.answer("⚠️ Такой промокод уже существует. Создайте другой код.")
        return
    await state.clear()
    promo = await db.get_promo(promo_id)
    await message.answer("✅ Обычный промокод создан.\n\n" + promo_detail_text(promo), reply_markup=promo_detail_kb(promo_id, True))


@router.callback_query(F.data == "promo_admin:list")
async def cb_promo_list(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    promos = await db.list_promos(20)
    await callback.message.edit_text(promos_list_text(promos), reply_markup=admin_promos_list_kb(promos))
    await callback.answer()


@router.callback_query(F.data.startswith("promo_admin:view:"))
async def cb_promo_view(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    promo_id = int(callback.data.split(":")[2])
    promo = await db.get_promo(promo_id)
    if promo is None:
        await callback.answer("⚠️ Промокод не найден.", show_alert=True)
        return
    await callback.message.edit_text(promo_detail_text(promo), reply_markup=promo_detail_kb(promo_id, bool(promo["is_active"])))
    await callback.answer()


@router.callback_query(F.data.startswith("promo_admin:toggle:"))
async def cb_promo_toggle(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    promo_id = int(callback.data.split(":")[2])
    await db.toggle_promo(promo_id)
    promo = await db.get_promo(promo_id)
    await callback.message.edit_text(promo_detail_text(promo), reply_markup=promo_detail_kb(promo_id, bool(promo["is_active"])))
    await callback.answer("✅ Готово.")


# Users
@router.callback_query(F.data == "admin:users")
async def cb_admin_users(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    await callback.message.edit_text("<b>👥 Клиенты VoxShop</b>\n━━━━━━━━━━━━\n\nПоиск, блокировки, баланс, заметки и права администратора.", reply_markup=users_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:users_search")
async def cb_admin_users_search(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    await state.set_state(AdminUserStates.search)
    await callback.message.edit_text("<b>🔎 Поиск клиента</b>\n\nВведите Telegram ID или username.\nПример: <code>7962973666</code> или <code>@username</code>", reply_markup=admin_back_kb())
    await callback.answer()


@router.message(AdminUserStates.search)
async def msg_admin_users_search(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    query = (message.text or "").strip()
    users = await db.search_users(query)
    await state.clear()
    if not users:
        await message.answer("⚠️ Клиенты не найдены.", reply_markup=users_menu_kb())
        return
    await message.answer("<b>🔎 Результаты поиска</b>\n\nВыберите клиента из списка:", reply_markup=users_search_results_kb(users))


@router.callback_query(F.data.startswith("adm:user:"))
async def cb_admin_user_detail(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    user_id = int(callback.data.split(":")[2])
    user = await db.get_user_by_id(user_id)
    if user is None:
        await callback.answer("⚠️ Клиент не найден.", show_alert=True)
        return
    stats = await db.get_user_order_stats(user_id)
    await callback.message.edit_text(admin_user_text(user, stats), reply_markup=user_admin_actions_kb(user_id, bool(user["is_banned"]), bool(user["is_admin"])))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:userban:"))
async def cb_admin_user_ban(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    _, _, raw_user_id, raw_ban = callback.data.split(":")
    user_id = int(raw_user_id)
    await db.set_user_banned(user_id, raw_ban == "1")
    user = await db.get_user_by_id(user_id)
    stats = await db.get_user_order_stats(user_id)
    await callback.message.edit_text(admin_user_text(user, stats), reply_markup=user_admin_actions_kb(user_id, bool(user["is_banned"]), bool(user["is_admin"])))
    await callback.answer("✅ Готово.")


@router.callback_query(F.data.startswith("adm:useradmin:"))
async def cb_admin_user_admin(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    _, _, raw_user_id, raw_admin = callback.data.split(":")
    user_id = int(raw_user_id)
    user = await db.get_user_by_id(user_id)
    if user is None:
        await callback.answer("⚠️ Клиент не найден.", show_alert=True)
        return
    await db.set_user_admin(user["telegram_id"], raw_admin == "1")
    user = await db.get_user_by_id(user_id)
    stats = await db.get_user_order_stats(user_id)
    await callback.message.edit_text(admin_user_text(user, stats), reply_markup=user_admin_actions_kb(user_id, bool(user["is_banned"]), bool(user["is_admin"])))
    await callback.answer("✅ Права обновлены.")


@router.callback_query(F.data.startswith("adm:userbalance:"))
async def cb_admin_user_balance(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    user_id = int(callback.data.split(":")[2])
    user = await db.get_user_by_id(user_id)
    if user is None:
        await callback.answer("Клиент не найден.", show_alert=True)
        return
    await state.set_state(AdminUserStates.balance)
    await state.update_data(user_id=user_id)
    await callback.message.edit_text(
        f"<b>💰 Изменить баланс</b>\n\nКлиент: <code>{user['telegram_id']}</code>\nСейчас: <b>{fmt_money(user['balance'])}</b>\n\nВведите новый баланс в рублях. Можно 0.",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminUserStates.balance)
async def msg_admin_user_balance(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    raw = (message.text or "").strip().replace(",", ".")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        await message.answer("⚠️ Введите число. Например: 250 или 0")
        return
    if value < 0:
        await message.answer("⚠️ Баланс не может быть меньше нуля.")
        return
    data = await state.get_data()
    user_id = int(data["user_id"])
    await db.set_user_balance(user_id, str(value))
    await state.clear()
    user = await db.get_user_by_id(user_id)
    stats = await db.get_user_order_stats(user_id)
    await message.answer("✅ Баланс обновлён.\n\n" + admin_user_text(user, stats), reply_markup=user_admin_actions_kb(user_id, bool(user["is_banned"]), bool(user["is_admin"])))


@router.callback_query(F.data.startswith("adm:usernote:"))
async def cb_admin_user_note(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    user_id = int(callback.data.split(":")[2])
    await state.set_state(AdminUserStates.note)
    await state.update_data(user_id=user_id)
    await callback.message.edit_text("<b>📝 Заметка о клиенте</b>\n\nВведите новый внутренний комментарий. Его видят только админы.", reply_markup=admin_back_kb())
    await callback.answer()


@router.message(AdminUserStates.note)
async def msg_admin_user_note(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    data = await state.get_data()
    user_id = int(data["user_id"])
    await db.set_user_note(user_id, (message.text or "").strip())
    await state.clear()
    user = await db.get_user_by_id(user_id)
    stats = await db.get_user_order_stats(user_id)
    await message.answer("✅ Заметка обновлена.\n\n" + admin_user_text(user, stats), reply_markup=user_admin_actions_kb(user_id, bool(user["is_banned"]), bool(user["is_admin"])))


@router.callback_query(F.data.startswith("adm:userorders:"))
async def cb_admin_user_orders(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    user_id = int(callback.data.split(":")[2])
    orders = await db.list_user_orders(user_id, category="all", limit=10)
    await callback.message.edit_text(orders_list_text(f"📦 Заявки клиента #{user_id}", orders), reply_markup=admin_back_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:addadmin")
async def cb_admin_addadmin(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    await state.set_state(AdminUserStates.add_admin)
    await callback.message.edit_text("<b>🛡 Выдать админку</b>\n\nВведите Telegram ID нового администратора.", reply_markup=admin_back_kb())
    await callback.answer()


@router.message(AdminUserStates.add_admin)
async def msg_admin_addadmin(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("⚠️ Введите числовой Telegram ID.")
        return
    telegram_id = int(raw)
    await db.set_user_admin(telegram_id, True)
    await state.clear()
    await message.answer(f"✅ Пользователь <code>{telegram_id}</code> получил права администратора.", reply_markup=admin_menu_kb())


# Mailing
@router.callback_query(F.data == "admin:mailing")
async def cb_admin_mailing(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    await state.set_state(AdminMailingStates.content)
    await callback.message.edit_text(
        "<b>📣 Рассылка VoxShop</b>\n\nОтправьте текст рассылки или фото с подписью. Заблокированным клиентам рассылка не отправляется.",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminMailingStates.content)
async def msg_admin_mailing_content(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    text = None
    photo_file_id = None
    if message.photo:
        photo_file_id = message.photo[-1].file_id
        text = message.caption
    elif message.text:
        text = message.text.strip()
    if not text and not photo_file_id:
        await message.answer("⚠️ Отправьте текст или фото с подписью.")
        return
    await state.update_data(text=text, photo_file_id=photo_file_id)
    await state.set_state(AdminMailingStates.preview)
    preview_note = "\n\n\nПредпросмотр рассылки. Нажмите кнопку ниже для запуска."
    if photo_file_id:
        await message.answer_photo(photo_file_id, caption=(text or "") + preview_note, reply_markup=mailing_confirm_kb(), parse_mode=None)
    else:
        await message.answer(f"{text}{preview_note}", reply_markup=mailing_confirm_kb(), parse_mode=None)


@router.callback_query(F.data == "mail:confirm")
async def cb_admin_mailing_confirm(callback: CallbackQuery, state: FSMContext, db: Database, config: Config, bot: Bot) -> None:
    if not await require_admin(callback, db, config):
        return
    data = await state.get_data()
    text = data.get("text")
    photo_file_id = data.get("photo_file_id")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("🚀 Рассылка запущена.")
    mailing_id, sent, failed = await run_mailing(bot, db, text=text, photo_file_id=photo_file_id)
    await state.clear()
    await callback.message.answer(f"✅ Рассылка #{mailing_id} завершена.\n📨 Отправлено: <b>{sent}</b>\n⚠️ Ошибок: <b>{failed}</b>", reply_markup=admin_menu_kb())
    if failed:
        await send_to_admins(bot, db, config, f"⚠️ В рассылке #{mailing_id} были ошибки: {failed}.")


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    stats = await db.get_stats()
    await callback.message.edit_text(stats_text(stats), reply_markup=admin_back_kb())
    await callback.answer()


# Support
@router.callback_query(F.data.startswith("admin:support"))
async def cb_admin_support(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    parts = callback.data.split(":")
    category = parts[2] if len(parts) > 2 else "open"
    if category not in {"open", "answered", "all"}:
        category = "open"
    tickets = await db.list_support_tickets(category, limit=12)
    title = {"open": "🟢 Открытые обращения", "answered": "✅ Отвеченные обращения", "all": "📚 Все обращения"}.get(category, "💬 Обращения")
    await callback.message.edit_text(support_tickets_text(title, tickets), reply_markup=support_tickets_list_kb(tickets, category))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:support_ticket:"))
async def cb_admin_support_ticket(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    ticket_id = int(callback.data.split(":")[2])
    ticket = await db.get_support_ticket(ticket_id)
    if ticket is None:
        await callback.answer("⚠️ Обращение не найдено.", show_alert=True)
        return
    await callback.message.edit_text(support_ticket_text(ticket), reply_markup=support_ticket_admin_kb(ticket_id))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:ticketreply:"))
async def cb_admin_ticket_reply(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    ticket_id = int(callback.data.split(":")[2])
    ticket = await db.get_support_ticket(ticket_id)
    if ticket is None:
        await callback.answer("⚠️ Обращение не найдено.", show_alert=True)
        return
    await state.set_state(AdminSupportStates.answer)
    await state.update_data(ticket_id=ticket_id)
    await callback.message.edit_text(f"<b>💬 Ответ на обращение #{ticket_id}</b>\n\nВведите текст ответа клиенту.", reply_markup=admin_back_kb())
    await callback.answer()


@router.message(AdminSupportStates.answer)
async def msg_admin_ticket_answer(message: Message, state: FSMContext, db: Database, config: Config, bot: Bot) -> None:
    if not await require_admin(message, db, config):
        return
    data = await state.get_data()
    ticket_id = int(data["ticket_id"])
    ticket = await db.get_support_ticket(ticket_id)
    if ticket is None:
        await state.clear()
        await message.answer("⚠️ Обращение не найдено.", reply_markup=admin_menu_kb())
        return
    answer = (message.text or "").strip()
    if len(answer) < 2:
        await message.answer("⚠️ Ответ слишком короткий.")
        return
    await db.answer_support_ticket(ticket_id, answer)
    await bot.send_message(ticket["telegram_id"], f"<b>💬 Ответ поддержки VoxShop</b>\n\nОбращение #{ticket_id}\n\n{h(answer)}")
    await state.clear()
    await message.answer("✅ Ответ отправлен клиенту.", reply_markup=admin_menu_kb())


# Reviews management
@router.callback_query(F.data == "admin:reviews")
async def cb_admin_reviews(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    total = await db.get_reviews_count()
    await callback.message.edit_text(
        "<b>⭐ Управление отзывами</b>\n"
        "━━━━━━━━━━━━\n"
        f"Всего отзывов: <b>{total}</b>\n\n"
        "Можно добавить ручной отзыв, посмотреть последние отзывы и удалить лишние.",
        reply_markup=admin_reviews_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "adm_reviews:list")
async def cb_admin_reviews_list(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    reviews = await db.list_reviews_admin(20)
    await callback.message.edit_text(admin_reviews_text(reviews), reply_markup=admin_reviews_list_kb(reviews))
    await callback.answer()


@router.callback_query(F.data.startswith("adm_reviews:view:"))
async def cb_admin_review_view(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    review_id = int(callback.data.split(":")[2])
    review = await db.get_review(review_id)
    if review is None:
        await callback.answer("Отзыв не найден.", show_alert=True)
        return
    await callback.message.edit_text(admin_review_detail_text(review), reply_markup=admin_review_detail_kb(review_id))
    await callback.answer()


@router.callback_query(F.data.startswith("adm_reviews:delete:"))
async def cb_admin_review_delete(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    review_id = int(callback.data.split(":")[2])
    await db.delete_review(review_id)
    reviews = await db.list_reviews_admin(20)
    await callback.message.edit_text("✅ Отзыв удалён.\n\n" + admin_reviews_text(reviews), reply_markup=admin_reviews_list_kb(reviews))
    await callback.answer("Удалено.")


@router.callback_query(F.data == "adm_reviews:add")
async def cb_admin_review_add(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    await state.clear()
    await state.set_state(AdminReviewStates.rating)
    await callback.message.edit_text(
        "<b>➕ Новый отзыв</b>\n"
        "━━━━━━━━━━━━\n"
        "Выберите оценку:",
        reply_markup=admin_review_rating_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_reviews:rating:"))
async def cb_admin_review_rating(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    rating = int(callback.data.split(":")[2])
    await state.update_data(rating=rating)
    await state.set_state(AdminReviewStates.name)
    await callback.message.edit_text(
        "<b>👤 Автор отзыва</b>\n"
        "━━━━━━━━━━━━\n"
        "Отправьте имя/username автора.\n"
        "Для анонимного отзыва отправьте <code>-</code>.",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminReviewStates.name)
async def msg_admin_review_name(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    raw = (message.text or "").strip()
    is_anonymous = raw in {"", "-", "анон", "Анон", "аноним", "Аноним"}
    display_name = "Аноним" if is_anonymous else raw[:80]
    await state.update_data(is_anonymous=is_anonymous, display_name=display_name)
    await state.set_state(AdminReviewStates.text)
    await message.answer(
        "<b>📝 Текст отзыва</b>\n"
        "━━━━━━━━━━━━\n"
        "Отправьте текст отзыва одним сообщением."
    )


@router.message(AdminReviewStates.text)
async def msg_admin_review_text(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    text = (message.text or "").strip()
    if len(text) < 3:
        await message.answer("⚠️ Текст слишком короткий.")
        return
    if len(text) > 700:
        text = short_text(text, 700)
    data = await state.get_data()
    review_id = await db.create_manual_review(
        rating=int(data.get("rating", 5)),
        text=text,
        display_name=data.get("display_name", "Аноним"),
        is_anonymous=bool(data.get("is_anonymous", True)),
    )
    await state.clear()
    await message.answer(f"✅ Отзыв #{review_id} добавлен.", reply_markup=admin_reviews_menu_kb())


# Bot control / maintenance mode
@router.callback_query(F.data == "admin:bot_control")
async def cb_admin_bot_control(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    enabled = (await db.get_setting("bot_enabled")) != "0"
    reason = await db.get_setting("bot_disabled_reason")
    await callback.message.edit_text(bot_control_text(enabled, reason), reply_markup=admin_bot_control_kb(enabled))
    await callback.answer()


@router.callback_query(F.data == "adm_bot:enable")
async def cb_admin_bot_enable(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    await db.set_setting("bot_enabled", "1")
    reason = await db.get_setting("bot_disabled_reason")
    await callback.message.edit_text(bot_control_text(True, reason), reply_markup=admin_bot_control_kb(True))
    await callback.answer("Бот включён.")


@router.callback_query(F.data == "adm_bot:disable")
async def cb_admin_bot_disable(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    await state.set_state(AdminBotControlStates.disable_reason)
    await callback.message.edit_text(
        "<b>🔴 Отключение бота</b>\n"
        "━━━━━━━━━━━━\n"
        "Напишите причину. Её увидят клиенты при /start и при нажатии кнопок.\n\n"
        "Пример: <code>Технические работы до 18:00</code>",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminBotControlStates.disable_reason)
async def msg_admin_bot_disable_reason(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    reason = (message.text or "").strip()
    if len(reason) < 3:
        await message.answer("⚠️ Напишите нормальную причину отключения.")
        return
    if len(reason) > 300:
        reason = short_text(reason, 300)
    await db.set_setting("bot_disabled_reason", reason)
    await db.set_setting("bot_enabled", "0")
    await state.clear()
    await message.answer(bot_control_text(False, reason), reply_markup=admin_bot_control_kb(False))


# ── Search orders by ID ──
@router.callback_query(F.data == "admin:search_order")
async def cb_admin_search_order(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    await state.set_state(AdminSearchOrderStates.query)
    await callback.message.edit_text(
        "<b>🔍 Поиск заявки</b>\n"
        "━━━━━━━━━━━━\n\n"
        "Введите номер заявки (ID).\n"
        "Например: <code>42</code>",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminSearchOrderStates.query)
async def msg_admin_search_order(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    query = (message.text or "").strip()
    orders = await db.search_orders(query)
    await state.clear()
    if not orders:
        await message.answer("Заявка не найдена.", reply_markup=admin_menu_kb())
        return
    order = orders[0]
    await message.answer(order_admin_text(order), reply_markup=admin_order_actions_kb(order["id"], order["order_type"]))


# ── Direct message to user ──
@router.callback_query(F.data == "admin:dm_user")
async def cb_admin_dm_user(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    await state.set_state(AdminDirectMessageStates.telegram_id)
    await callback.message.edit_text(
        "<b>📩 Сообщение клиенту</b>\n"
        "━━━━━━━━━━━━\n\n"
        "Введите Telegram ID пользователя.\n"
        "Например: <code>123456789</code>",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminDirectMessageStates.telegram_id)
async def msg_admin_dm_user_id(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not await require_admin(message, db, config):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("⚠️ Введите числовой Telegram ID.", reply_markup=admin_back_kb())
        return
    await state.update_data(target_telegram_id=int(raw))
    await state.set_state(AdminDirectMessageStates.text)
    await message.answer(
        f"Получатель: <code>{raw}</code>\n\n"
        "Теперь введите текст сообщения:",
        reply_markup=admin_back_kb(),
    )


@router.message(AdminDirectMessageStates.text)
async def msg_admin_dm_user_text(message: Message, state: FSMContext, db: Database, config: Config, bot: Bot) -> None:
    if not await require_admin(message, db, config):
        return
    data = await state.get_data()
    target_tg = data.get("target_telegram_id")
    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("⚠️ Сообщение слишком короткое.")
        return
    await state.clear()
    try:
        await bot.send_message(
            target_tg,
            f"<b>📩 Сообщение от администрации VoxShop</b>\n"
            f"━━━━━━━━━━━━\n\n"
            f"{h(text)}",
        )
        await message.answer(f"✅ Сообщение отправлено пользователю <code>{target_tg}</code>.", reply_markup=admin_menu_kb())
    except Exception as e:
        await message.answer(f"⚠️ Не удалось отправить: {h(str(e))}", reply_markup=admin_menu_kb())


# ── Top clients ──
@router.callback_query(F.data == "admin:top_clients")
async def cb_admin_top_clients(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    clients = await db.get_top_clients(10)
    if not clients:
        await callback.message.edit_text("Пока нет клиентов с заявками.", reply_markup=admin_back_kb())
        await callback.answer()
        return
    lines = ["<b>🏆 Топ клиентов</b>", "━━━━━━━━━━━━", ""]
    for i, c in enumerate(clients, 1):
        name = f"@{c['username']}" if c["username"] else c["first_name"] or "без имени"
        lines.append(
            f"<b>{i}.</b>  {h(name)}\n"
            f"     📦 Заявок: <b>{c['order_count']}</b>  ·  💰 Сумма: <b>{fmt_money(c['total_spent'])}</b>"
        )
        lines.append("")
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_back_kb())
    await callback.answer()


# ── Recent users ──
@router.callback_query(F.data == "admin:recent_users")
async def cb_admin_recent_users(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await require_admin(callback, db, config):
        return
    users = await db.get_recent_users(15)
    total = await db.get_all_users_count()
    if not users:
        await callback.message.edit_text("Пользователей пока нет.", reply_markup=admin_back_kb())
        await callback.answer()
        return
    lines = [
        "<b>🆕 Новые пользователи</b>",
        "━━━━━━━━━━━━",
        "",
        f"Всего активных: <b>{total}</b>",
        "",
    ]
    for u in users:
        name = f"@{u['username']}" if u["username"] else u["first_name"] or "без имени"
        ban = " 🚫" if u["is_banned"] else ""
        lines.append(f"• {h(name)}  <code>{u['telegram_id']}</code>{ban}")
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_back_kb())
    await callback.answer()
