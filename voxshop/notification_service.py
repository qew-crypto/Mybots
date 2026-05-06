from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from config import Config
from database import Database
from keyboards import admin_order_actions_kb, admin_topup_actions_kb, review_order_kb, support_ticket_admin_kb
from order_service import order_admin_text, status_name, topup_admin_text
from utils import h

logger = logging.getLogger(__name__)


async def get_all_admin_ids(db: Database, config: Config) -> list[int]:
    ids = set(config.admin_ids)
    for admin_id in await db.get_admin_telegram_ids():
        ids.add(admin_id)
    return sorted(ids)


async def send_to_admins(
    bot: Bot,
    db: Database,
    config: Config,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    photo_file_id: str | None = None,
    document_file_id: str | None = None,
) -> tuple[int, int]:
    sent = 0
    failed = 0
    for admin_id in await get_all_admin_ids(db, config):
        try:
            if photo_file_id:
                await bot.send_photo(admin_id, photo_file_id, caption=text, reply_markup=reply_markup)
            elif document_file_id:
                await bot.send_document(admin_id, document_file_id, caption=text, reply_markup=reply_markup)
            else:
                await bot.send_message(admin_id, text, reply_markup=reply_markup)
            sent += 1
        except Exception:
            failed += 1
            logger.exception("Failed to notify admin %s", admin_id)
    return sent, failed


async def notify_new_order(
    bot: Bot,
    db: Database,
    config: Config,
    order_id: int,
    *,
    receipt_file_id: str | None = None,
    receipt_file_type: str | None = None,
) -> None:
    order = await db.get_order_with_user(order_id)
    if order is None:
        return

    title = "💎 Новая покупка" if order["order_type"] == "buy" else "🤝 Новая продажа"
    text = f"<b>{title}</b>\n\n{order_admin_text(order)}"

    await send_to_admins(
        bot,
        db,
        config,
        text,
        reply_markup=admin_order_actions_kb(order_id, order["order_type"]),
    )

    if receipt_file_id:
        caption = f"Чек / файл к заявке #{order_id}"
        for admin_id in await get_all_admin_ids(db, config):
            try:
                if receipt_file_type == "photo":
                    await bot.send_photo(admin_id, receipt_file_id, caption=caption)
                elif receipt_file_type == "document":
                    await bot.send_document(admin_id, receipt_file_id, caption=caption)
            except Exception:
                logger.exception("Failed to forward receipt for order %s to admin %s", order_id, admin_id)


async def notify_order_status(bot: Bot, db: Database, order_id: int, status: str) -> None:
    order = await db.get_order_with_user(order_id)
    if order is None:
        return

    settings = await db.get_settings()
    support = settings.get("support_contact", "@kawalskuy")
    if order["order_type"] == "buy":
        completed_text = "Заявка завершена. Голда выдана. Можете оставить отзыв о покупке."
    else:
        completed_text = "Заявка завершена. Выплата проведена. Можете оставить отзыв о продаже."
    text_by_status = {
        "paid": f"Оплата подтверждена. Для получения голды напишите в поддержку {support}.",
        "in_progress": f"Заявка в работе. По деталям можно написать в поддержку {support}.",
        "completed": completed_text,
        "rejected": f"Заявка отклонена. Если использовался баланс, он автоматически вернётся. За подробностями напишите {support}.",
        "cancelled": f"Заявка отменена. Если использовался баланс, он автоматически вернётся. За подробностями напишите {support}.",
        "new": "Заявка получила статус: новая.",
        "waiting_payment": "Заявка ожидает проверки оплаты.",
    }
    text = (
        f"<b>📦 Обновление заявки #{order_id}</b>\n\n"
        f"Статус: <b>{h(status_name(status))}</b>\n\n"
        f"{h(text_by_status.get(status, 'Статус заявки изменён.'))}"
    )
    try:
        await bot.send_message(
            order["telegram_id"],
            text,
            reply_markup=review_order_kb(order_id) if status == "completed" else None,
        )
    except Exception:
        logger.exception("Failed to notify user about order %s status", order_id)


async def notify_new_topup(
    bot: Bot,
    db: Database,
    config: Config,
    topup_id: int,
    *,
    receipt_file_id: str | None = None,
    receipt_file_type: str | None = None,
) -> None:
    topup = await db.get_topup_with_user(topup_id)
    if topup is None:
        return
    await send_to_admins(
        bot,
        db,
        config,
        f"<b>💳 Новое пополнение баланса</b>\n\n{topup_admin_text(topup)}",
        reply_markup=admin_topup_actions_kb(topup_id, topup["status"]),
    )
    if receipt_file_id:
        caption = f"Чек / файл к пополнению #{topup_id}"
        for admin_id in await get_all_admin_ids(db, config):
            try:
                if receipt_file_type == "photo":
                    await bot.send_photo(admin_id, receipt_file_id, caption=caption)
                elif receipt_file_type == "document":
                    await bot.send_document(admin_id, receipt_file_id, caption=caption)
            except Exception:
                logger.exception("Failed to forward topup receipt %s to admin %s", topup_id, admin_id)


async def notify_support_ticket(
    bot: Bot,
    db: Database,
    config: Config,
    ticket_id: int,
) -> None:
    ticket = await db.get_support_ticket(ticket_id)
    if ticket is None:
        return
    username = f"@{ticket['username']}" if ticket["username"] else ticket["first_name"] or "без username"
    text = (
        f"<b>💬 Новое обращение #{ticket['id']}</b>\n\n"
        f"Клиент: {h(username)} · <code>{ticket['telegram_id']}</code>\n\n"
        f"<b>Сообщение:</b>\n{h(ticket['message'])}"
    )
    await send_to_admins(
        bot,
        db,
        config,
        text,
        reply_markup=support_ticket_admin_kb(ticket_id),
    )
