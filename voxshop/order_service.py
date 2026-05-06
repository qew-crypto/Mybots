from __future__ import annotations

from models import ORDER_STATUSES, ORDER_TYPE_NAMES, SETTING_TITLES, TOPUP_STATUSES
from utils import fmt_gold, fmt_money, h, short_text, yes_no

SEP = "━━━━━━━━━━━━"


def status_name(status: str) -> str:
    return ORDER_STATUSES.get(status, status)


def topup_status_name(status: str) -> str:
    return TOPUP_STATUSES.get(status, status)


def type_name(order_type: str) -> str:
    return ORDER_TYPE_NAMES.get(order_type, order_type)


def stars(rating: int | str) -> str:
    value = max(1, min(5, int(rating)))
    return "⭐" * value + "☆" * (5 - value)


def _is_url(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().startswith(("https://", "http://"))


def payment_method_url(method) -> str | None:
    raw = method["card_number"] if method else None
    if _is_url(raw):
        return str(raw).strip()
    return None


def payment_method_public(method) -> str:
    lines = [f"<b>{h(method['title'])}</b>"]
    if method["bank_name"]:
        lines.append(f"{h(method['bank_name'])}")
    if method["card_number"] and not _is_url(method["card_number"]):
        lines.append(f"Карта / счёт: <code>{h(method['card_number'])}</code>")
    if method["phone_number"]:
        lines.append(f"СБП / телефон: <code>{h(method['phone_number'])}</code>")
    if method["recipient_name"]:
        lines.append(f"Получатель: <b>{h(method['recipient_name'])}</b>")
    if method["comment"]:
        lines.append(f"Комментарий: {h(method['comment'])}")
    return "\n".join(lines)


def payment_method_plain(method) -> str:
    lines = [str(method["title"])]
    if method["bank_name"]:
        lines.append(f"Описание: {method['bank_name']}")
    if method["card_number"]:
        lines.append(f"Ссылка / карта: {method['card_number']}")
    if method["phone_number"]:
        lines.append(f"СБП / телефон: {method['phone_number']}")
    if method["recipient_name"]:
        lines.append(f"Получатель: {method['recipient_name']}")
    if method["comment"]:
        lines.append(f"Комментарий: {method['comment']}")
    return "\n".join(lines)


def settings_text(settings: dict[str, str], section: str = "rates") -> str:
    if section == "texts":
        keys = ["bot_name", "support_contact", "welcome_text", "after_buy_text", "after_sell_text", "faq_text"]
        lines = [
            "<b>📝 Тексты и контакты</b>",
            SEP,
            "Здесь меняются название, поддержка, приветствие и FAQ.",
        ]
    else:
        keys = ["sell_rate_to_user", "buy_rate_from_user", "min_buy_gold", "min_sell_gold", "max_gold"]
        lines = [
            "<b>💱 Курсы и лимиты</b>",
            SEP,
            "Эти значения используются при расчёте заявок.",
        ]

    for key in keys:
        title = SETTING_TITLES.get(key, key)
        value = settings.get(key, "")
        if len(value) > 150:
            value = short_text(value, 150)
        lines.append(f"\n<b>{h(title)}</b>\n<code>{h(value)}</code>")
    return "\n".join(lines)


def order_user_text(order) -> str:
    balance_used = order["balance_used"] if "balance_used" in order.keys() else "0"
    payment_due = order["payment_due"] if "payment_due" in order.keys() else order["total_amount"]
    return (
        f"<b>📦 Заявка #{order['id']}</b>\n"
        f"{SEP}\n\n"
        f"📌 Тип:  <b>{h(type_name(order['order_type']))}</b>\n"
        f"🔄 Статус:  <b>{h(status_name(order['status']))}</b>\n"
        f"\n{SEP}\n\n"
        f"💎 Голда:  <b>{fmt_gold(order['gold_amount'])}</b>\n"
        f"💱 Курс:  <b>{h(order['rate'])} ₽</b>\n"
        f"💰 Сумма:  <b>{fmt_money(order['total_amount'])}</b>\n\n"
        f"📥 С баланса:  <b>{fmt_money(balance_used)}</b>\n"
        f"💳 К оплате:  <b>{fmt_money(payment_due)}</b>\n"
        f"\n📅 <code>{h(order['created_at'])}</code>"
    )


def order_admin_text(order, user=None) -> str:
    if user:
        username = f"@{user['username']}" if user["username"] else (user["first_name"] or "без username")
        telegram_id = user["telegram_id"]
    else:
        username = f"@{order['username']}" if order["username"] else (order["first_name"] or "без username")
        telegram_id = order["telegram_id"]

    balance_used = order["balance_used"] if "balance_used" in order.keys() else "0"
    payment_due = order["payment_due"] if "payment_due" in order.keys() else order["total_amount"]
    parts = [
        f"<b>📦 Заявка #{order['id']}</b>",
        SEP,
        "",
        f"📌 Тип:  <b>{h(type_name(order['order_type']))}</b>",
        f"👤 Клиент:  {h(username)} · <code>{telegram_id}</code>",
        f"🔄 Статус:  <b>{h(status_name(order['status']))}</b>",
        "",
        SEP,
        "",
        f"💎 Голда:  <b>{fmt_gold(order['gold_amount'])}</b>",
        f"💱 Курс:  <b>{h(order['rate'])} ₽</b>",
        f"💰 Сумма:  <b>{fmt_money(order['total_amount'])}</b>",
        f"📥 С баланса:  <b>{fmt_money(balance_used)}</b>",
        f"💳 К оплате:  <b>{fmt_money(payment_due)}</b>",
        "",
        f"📅 <code>{h(order['created_at'])}</code>",
    ]
    if order["payment_details"]:
        parts.extend(["", SEP, "", f"<b>🏦 Оплата</b>", f"{h(order['payment_details'])}"])
    if order["user_payment_details"]:
        parts.extend(["", SEP, "", f"<b>📋 Реквизиты клиента</b>", f"{h(order['user_payment_details'])}"])
    if order["receipt_file_id"]:
        parts.extend(["", f"📎 Чек / файл: <b>есть</b> ({h(order['receipt_file_type'] or 'file')})"])
    if order["comment"]:
        parts.extend(["", f"<b>💬 Комментарий</b>", f"{h(order['comment'])}"])
    return "\n".join(parts)


def orders_list_text(title: str, orders) -> str:
    if not orders:
        return f"<b>{h(title)}</b>\n{SEP}\n\nПока пусто."
    lines = [f"<b>{h(title)}</b>", SEP]
    for order in orders:
        lines.append(
            f"\n<b>#{order['id']} · {h(type_name(order['order_type']))}</b>\n"
            f"💎 {fmt_gold(order['gold_amount'])} · 💸 {fmt_money(order['total_amount'])}\n"
            f"Статус: <b>{h(status_name(order['status']))}</b>\n"
            f"<code>{h(order['created_at'])}</code>"
        )
    return "\n".join(lines)


def profile_text(user, stats: dict) -> str:
    username = f"@{user['username']}" if user["username"] else "не указан"
    status = "заблокирован" if user["is_banned"] else "активен"
    admin = " · администратор" if user["is_admin"] else ""
    return (
        "<b>👤 Профиль</b>\n"
        f"{SEP}\n\n"
        f"🆔  <code>{user['telegram_id']}</code>\n"
        f"👤  <b>{h(username)}</b>\n"
        f"📌  {h(status + admin)}\n"
        f"\n{SEP}\n\n"
        f"💰 <b>Баланс:</b>  <b>{fmt_money(user['balance'])}</b>\n"
        f"📥 Пополнено:  {fmt_money(stats.get('topup_sum', 0))}\n"
        f"\n{SEP}\n\n"
        f"📦 <b>Сделки</b>\n\n"
        f"  Покупок:  <b>{stats['buy_count']}</b>\n"
        f"  Продаж:  <b>{stats['sell_count']}</b>\n"
        f"  Сумма:  <b>{fmt_money(stats['total_sum'])}</b>\n"
        f"\n{SEP}\n\n"
        f"⭐ Ваших отзывов: <b>{stats.get('review_count', 0)}</b>"
    )


def referral_text(user, stats: dict, ref_link: str) -> str:
    return (
        "<b>🎁 Реферальная система</b>\n"
        f"{SEP}\n\n"
        "Приглашайте друзей и получайте <b>10%</b> бонус\n"
        "от каждого подтверждённого пополнения.\n\n"
        f"{SEP}\n\n"
        f"👥 Ваших рефералов:  <b>{stats.get('ref_count', 0)}</b>\n"
        f"💰 Бонусов получено:  <b>{fmt_money(user['ref_bonus_total'])}</b>\n\n"
        f"{SEP}\n\n"
        f"🔗 <b>Ваша ссылка:</b>\n"
        f"<code>{h(ref_link)}</code>\n\n"
        "Отправьте эту ссылку друзьям.\n"
        "Новый пользователь, пришедший по ней, автоматически станет вашим рефералом."
    )


def admin_user_text(user, stats: dict | None = None) -> str:
    username = f"@{user['username']}" if user["username"] else "не указан"
    text = (
        f"<b>👤 Пользователь #{user['id']}</b>\n"
        f"{SEP}\n"
        f"Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"Username: {h(username)}\n"
        f"Имя: {h(user['first_name'] or '-')}\n"
        f"Регистрация: <code>{h(user['registered_at'])}</code>\n"
        f"Баланс: <b>{fmt_money(user['balance'])}</b>\n"
        f"Реф-бонусы: <b>{fmt_money(user['ref_bonus_total'])}</b>\n"
        f"Пригласил user_id: <code>{h(user['referrer_user_id'] or '-')}</code>\n"
        f"Админ: <b>{yes_no(user['is_admin'])}</b>\n"
        f"Блокировка: <b>{yes_no(user['is_banned'])}</b>\n"
        f"Заметка: {h(user['note'] or '-')}"
    )
    if stats:
        text += (
            f"\n\n<b>Сделки</b>"
            f"\nПокупок: <b>{stats['buy_count']}</b>"
            f"\nПродаж: <b>{stats['sell_count']}</b>"
            f"\nСумма: <b>{fmt_money(stats['total_sum'])}</b>"
            f"\nПополнено: <b>{fmt_money(stats.get('topup_sum', 0))}</b>"
            f"\nРефералов: <b>{stats.get('ref_count', 0)}</b>"
        )
    return text


def payment_methods_text(methods) -> str:
    if not methods:
        return (
            "<b>🏦 Реквизиты</b>\n"
            f"{SEP}\n\n"
            "Реквизиты ещё не добавлены. Нажмите кнопку ниже, чтобы создать первые."
        )
    lines = [
        "<b>🏦 Реквизиты</b>",
        SEP,
        "Активный DonateAlerts показывается клиенту кнопкой оплаты.",
    ]
    for method in methods:
        status = "активны" if method["is_active"] else "выключены"
        link = "ссылка скрыта в кнопке" if _is_url(method["card_number"]) else h(method["card_number"] or "-")
        lines.append(
            f"\n<b>#{method['id']} · {h(method['title'])}</b> — {status}\n"
            f"Описание: {h(method['bank_name'] or '-')}\n"
            f"Ссылка / карта: {link}\n"
            f"СБП / телефон: {h(method['phone_number'] or '-')}\n"
            f"Получатель: {h(method['recipient_name'] or '-')}\n"
            f"Комментарий: {h(short_text(method['comment'] or '-', 120))}"
        )
    return "\n".join(lines)


def payment_method_admin_text(method) -> str:
    status = "активны" if method["is_active"] else "выключены"
    return (
        f"<b>🏦 Реквизиты #{method['id']}</b>\n"
        f"{SEP}\n"
        f"Статус: <b>{status}</b>\n"
        f"Название: <b>{h(method['title'])}</b>\n"
        f"Описание: {h(method['bank_name'] or '-')}\n"
        f"Ссылка / карта: <code>{h(method['card_number'] or '-')}</code>\n"
        f"СБП / телефон: <code>{h(method['phone_number'] or '-')}</code>\n"
        f"Получатель: {h(method['recipient_name'] or '-')}\n"
        f"Комментарий: {h(method['comment'] or '-')}"
    )


def reviews_text(total: int, reviews, avg_rating: float = 4.8) -> str:
    avg_stars_full = int(avg_rating)
    avg_half = "." + str(int((avg_rating - avg_stars_full) * 10)) if avg_rating != int(avg_rating) else ""
    lines = [
        "<b>⭐ Отзывы VoxShop</b>",
        SEP,
        "",
        f"{'⭐' * avg_stars_full} <b>{avg_rating}</b> из 5",
        f"Всего отзывов: <b>{total}</b>",
        "",
        "━ Последние отзывы ━",
    ]
    if not reviews:
        lines.append("\nПока отзывов нет.")
        return "\n".join(lines)
    for review in reviews:
        name = "Аноним" if review["is_anonymous"] else review["display_name"]
        lines.append(
            f"\n{'⭐' * int(review['rating'])} · <b>{h(name)}</b>\n"
            f"{h(short_text(review['text'], 230))}"
        )
    return "\n".join(lines)


def topup_admin_text(topup) -> str:
    username = f"@{topup['username']}" if topup["username"] else topup["first_name"] or "без username"
    text = (
        f"<b>💳 Пополнение #{topup['id']}</b>\n"
        f"{SEP}\n\n"
        f"👤 Клиент:  {h(username)} · <code>{topup['telegram_id']}</code>\n"
        f"💰 Сумма:  <b>{fmt_money(topup['amount'])}</b>\n"
        f"🔄 Статус:  <b>{h(topup_status_name(topup['status']))}</b>\n"
        f"🎁 Реф-бонус:  <b>{fmt_money(topup['ref_bonus_paid'])}</b>\n\n"
        f"📅 <code>{h(topup['created_at'])}</code>"
    )
    if topup["payment_details"]:
        text += f"\n\n{SEP}\n\n<b>🏦 Оплата</b>\n{h(topup['payment_details'])}"
    if topup["receipt_file_id"]:
        text += f"\n\n📎 Чек / файл: <b>есть</b> ({h(topup['receipt_file_type'] or 'file')})"
    if topup["comment"]:
        text += f"\n\n<b>💬 Комментарий</b>\n{h(topup['comment'])}"
    return text


def topups_list_text(title: str, topups) -> str:
    if not topups:
        return f"<b>{h(title)}</b>\n{SEP}\n\nПополнений в этом разделе нет."
    lines = [f"<b>{h(title)}</b>", SEP]
    for topup in topups:
        username = f"@{topup['username']}" if topup["username"] else topup["first_name"] or "клиент"
        lines.append(
            f"\n<b>#{topup['id']} · {fmt_money(topup['amount'])}</b>\n"
            f"{h(username)} · {h(topup_status_name(topup['status']))}\n"
            f"<code>{h(topup['created_at'])}</code>"
        )
    return "\n".join(lines)


def promos_list_text(promos) -> str:
    if not promos:
        return f"<b>🎁 Промокоды</b>\n{SEP}\n\nПромокодов пока нет."
    lines = ["<b>🎁 Промокоды</b>", SEP]
    for promo in promos:
        status = "активен" if promo["is_active"] else "выключен"
        kind = "уникальный" if promo["is_unique"] else "обычный"
        lines.append(
            f"\n<b>{h(promo['code'])}</b> · {h(kind)}\n"
            f"Сумма: <b>{fmt_money(promo['amount'])}</b>\n"
            f"Активации: <b>{promo['activations_count']}/{promo['max_activations']}</b>\n"
            f"Статус: <b>{status}</b>"
        )
    return "\n".join(lines)


def promo_detail_text(promo) -> str:
    status = "активен" if promo["is_active"] else "выключен"
    kind = "Уникальный одноразовый" if promo["is_unique"] else "Обычный"
    return (
        f"<b>🎁 Промокод #{promo['id']}</b>\n"
        f"{SEP}\n"
        f"Код: <code>{h(promo['code'])}</code>\n"
        f"Тип: <b>{kind}</b>\n"
        f"Сумма: <b>{fmt_money(promo['amount'])}</b>\n"
        f"Активации: <b>{promo['activations_count']}/{promo['max_activations']}</b>\n"
        f"Статус: <b>{status}</b>\n"
        f"Создан: <code>{h(promo['created_at'])}</code>"
    )


def stats_text(stats: dict) -> str:
    return (
        "<b>📊 Статистика VoxShop</b>\n"
        f"{SEP}\n\n"
        f"👥 Пользователей:  <b>{stats['total_users']}</b>\n"
        f"🆕 Новых сегодня:  <b>{stats['today_users']}</b>\n"
        f"\n{SEP}\n\n"
        f"<b>📦 Заявки</b>\n\n"
        f"  Покупок:  <b>{stats['buy_count']}</b>\n"
        f"  Продаж:  <b>{stats['sell_count']}</b>\n"
        f"  Завершённых:  <b>{stats['completed_count']}</b>\n"
        f"  Отклонённых:  <b>{stats['rejected_count']}</b>\n"
        f"\n{SEP}\n\n"
        f"<b>💰 Баланс</b>\n\n"
        f"  Пополнений:  <b>{stats['topup_count']}</b>\n"
        f"  Ожидают проверки:  <b>{stats['topup_waiting']}</b>\n"
        f"  Зачислено:  <b>{fmt_money(stats['topup_sum'])}</b>\n"
        f"  Баланс клиентов:  <b>{fmt_money(stats['balance_sum'])}</b>\n"
        f"\n{SEP}\n\n"
        f"<b>💵 Финансы</b>\n\n"
        f"  Продажи клиентам:  <b>{fmt_money(stats['buy_sum'])}</b>\n"
        f"  Выкуп у клиентов:  <b>{fmt_money(stats['sell_sum'])}</b>\n"
        f"  Условная прибыль:  <b>{fmt_money(stats['gross_profit'])}</b>\n"
        f"\n{SEP}\n\n"
        f"⭐ Отзывов:  <b>{stats['review_count']}</b>  ·  🎁 Промокодов:  <b>{stats['promo_count']}</b>"
    )


def support_ticket_text(ticket) -> str:
    username = f"@{ticket['username']}" if ticket["username"] else ticket["first_name"] or "без username"
    text = (
        f"<b>💬 Обращение #{ticket['id']}</b>\n"
        f"{SEP}\n"
        f"Клиент: {h(username)} · <code>{ticket['telegram_id']}</code>\n"
        f"Статус: <b>{h(ticket['status'])}</b>\n"
        f"Дата: <code>{h(ticket['created_at'])}</code>\n\n"
        f"<b>Сообщение клиента:</b>\n{h(ticket['message'])}"
    )
    if ticket["admin_answer"]:
        text += f"\n\n<b>Ответ поддержки:</b>\n{h(ticket['admin_answer'])}"
    return text


def support_tickets_text(title: str, tickets) -> str:
    if not tickets:
        return f"<b>{h(title)}</b>\n{SEP}\n\nОбращений в этом разделе нет."
    lines = [f"<b>{h(title)}</b>", SEP]
    for ticket in tickets:
        username = f"@{ticket['username']}" if ticket["username"] else ticket["first_name"] or "без username"
        status = "открыто" if ticket["status"] == "open" else "отвечено"
        lines.append(
            f"\n<b>#{ticket['id']} · {h(username)}</b>\n"
            f"Статус: {status}\n"
            f"<code>{h(ticket['created_at'])}</code>\n"
            f"{h(short_text(ticket['message'], 100))}"
        )
    return "\n".join(lines)


def admin_reviews_text(reviews) -> str:
    if not reviews:
        return f"<b>⭐ Отзывы VoxShop</b>\n{SEP}\n\nОтзывов пока нет."
    lines = ["<b>⭐ Отзывы VoxShop</b>", SEP, "Ниже последние отзывы. Нажмите на отзыв, чтобы удалить его."]
    for review in reviews:
        name = "Аноним" if review["is_anonymous"] else review["display_name"]
        lines.append(
            f"\n<b>#{review['id']} · {stars(review['rating'])}</b>\n"
            f"Автор: {h(name)}\n"
            f"{h(short_text(review['text'], 180))}\n"
            f"<code>{h(review['created_at'])}</code>"
        )
    return "\n".join(lines)


def admin_review_detail_text(review) -> str:
    name = "Аноним" if review["is_anonymous"] else review["display_name"]
    source = "стартовый" if review["is_seed"] else "ручной/клиентский"
    return (
        f"<b>⭐ Отзыв #{review['id']}</b>\n"
        f"{SEP}\n"
        f"Оценка: <b>{stars(review['rating'])}</b>\n"
        f"Автор: <b>{h(name)}</b>\n"
        f"Тип: <b>{source}</b>\n"
        f"Дата: <code>{h(review['created_at'])}</code>\n\n"
        f"{h(review['text'])}"
    )


def bot_control_text(enabled: bool, reason: str) -> str:
    status = "🟢 включён" if enabled else "🔴 отключён"
    return (
        "<b>🤖 Управление ботом</b>\n"
        f"{SEP}\n"
        f"Статус: <b>{status}</b>\n\n"
        f"Причина отключения:\n<code>{h(reason or 'Не указана')}</code>\n\n"
        "Когда бот отключён, клиенты при /start и нажатии кнопок увидят эту причину. Админы смогут пользоваться панелью."
    )
