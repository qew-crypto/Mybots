from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from models import NUMERIC_SETTINGS, ORDER_STATUSES, SETTING_TITLES, TEXT_SETTINGS, TOPUP_STATUSES


def support_url(contact: str | None) -> str | None:
    if not contact:
        return None
    value = contact.strip()
    if value.startswith("@") and len(value) > 1:
        return f"https://t.me/{value[1:]}"
    if value.startswith(("https://", "http://")):
        return value
    return None


def ikb(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=data) for text, data in row]
            for row in rows
        ]
    )


def main_menu_kb() -> InlineKeyboardMarkup:
    return ikb(
        [
            [("💎 Купить голду", "buy:start"), ("🤝 Продать", "sell:start")],
            [("👤 Профиль", "user:profile"), ("⭐ Отзывы", "reviews:show")],
            [("📦 Мои заявки", "orders:menu"), ("🎁 Рефералы", "user:referral")],
            [("💬 Поддержка", "support:start"), ("📘 Правила / FAQ", "faq:show")],
        ]
    )

def back_to_menu_kb() -> InlineKeyboardMarkup:
    return ikb([[("🏠 Главное меню", "menu")]])


def cancel_kb() -> InlineKeyboardMarkup:
    return ikb([[("✖️ Отменить действие", "flow:cancel")]])


def profile_kb() -> InlineKeyboardMarkup:
    return ikb(
        [
            [("💰 Пополнить баланс", "topup:start")],
            [("🎁 Активировать промокод", "promo:start")],
            [("⭐ Смотреть отзывы", "reviews:show"), ("📦 Мои заявки", "orders:menu")],
            [("🏠 Главное меню", "menu")],
        ]
    )

def buy_choice_kb(*, can_pay_balance: bool, can_use_partial: bool) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = []
    if can_pay_balance:
        rows.append([("✅ Оплатить балансом", "buy:pay_balance")])
    if can_use_partial:
        rows.append([("💰 Списать баланс + доплатить", "buy:pay_mixed")])
    rows.append([("💳 Оплатить через DonateAlerts", "buy:pay_donate")])
    rows.append([("✖️ Отменить", "flow:cancel")])
    return ikb(rows)


def buy_payment_kb(payment_url: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if payment_url:
        rows.append([InlineKeyboardButton(text="💳 Оплатить в DonateAlerts", url=payment_url)])
    rows.append([InlineKeyboardButton(text="📎 Как отправить чек?", callback_data="buy:receipt_help")])
    rows.append([InlineKeyboardButton(text="✖️ Отменить", callback_data="flow:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def topup_payment_kb(payment_url: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if payment_url:
        rows.append([InlineKeyboardButton(text="💳 Пополнить через DonateAlerts", url=payment_url)])
    rows.append([InlineKeyboardButton(text="📎 Я оплатил, отправлю чек", callback_data="topup:receipt_help")])
    rows.append([InlineKeyboardButton(text="✖️ Отменить", callback_data="flow:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def orders_menu_kb() -> InlineKeyboardMarkup:
    return ikb(
        [
            [("🟡 Активные", "orders:active")],
            [("✅ Завершённые", "orders:completed"), ("⛔ Отклонённые", "orders:rejected")],
            [("🏠 Главное меню", "menu")],
        ]
    )


def support_menu_kb(support_contact: str | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    url = support_url(support_contact)
    if url:
        rows.append([InlineKeyboardButton(text="💬 Написать в поддержку", url=url)])
    rows.append([InlineKeyboardButton(text="📝 Создать обращение в боте", callback_data="support:create")])
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_created_user_kb(support_contact: str | None = None, order_id: int | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    url = support_url(support_contact)
    if url:
        rows.append([InlineKeyboardButton(text="💬 Написать в поддержку", url=url)])
    else:
        rows.append([InlineKeyboardButton(text="💬 Поддержка", callback_data="support:start")])
    rows.append(
        [
            InlineKeyboardButton(text="📦 Мои заявки", callback_data="orders:menu"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reviews_kb() -> InlineKeyboardMarkup:
    return ikb(
        [
            [("⭐ Оставить отзыв", "review:general")],
            [("🔄 Обновить", "reviews:show"), ("🏠 Меню", "menu")],
        ]
    )

def review_order_kb(order_id: int) -> InlineKeyboardMarkup:
    return ikb(
        [
            [("⭐ Оставить отзыв", f"review:start:{order_id}")],
            [("📦 Мои заявки", "orders:menu"), ("🏠 Меню", "menu")],
        ]
    )


def review_rating_kb() -> InlineKeyboardMarkup:
    return ikb(
        [
            [("⭐", "review:rating:1"), ("⭐⭐", "review:rating:2"), ("⭐⭐⭐", "review:rating:3")],
            [("⭐⭐⭐⭐", "review:rating:4"), ("⭐⭐⭐⭐⭐", "review:rating:5")],
            [("✖️ Отменить", "flow:cancel")],
        ]
    )


def review_visibility_kb() -> InlineKeyboardMarkup:
    return ikb(
        [
            [("🕶 Анонимно", "review:visibility:anon")],
            [("👤 С моим username", "review:visibility:user")],
            [("✖️ Отменить", "flow:cancel")],
        ]
    )


# Admin keyboards

def admin_menu_kb() -> InlineKeyboardMarkup:
    return ikb(
        [
            [("📦 Заявки", "admin:orders"), ("💳 Пополнения", "admin:topups")],
            [("🎁 Промокоды", "admin:promos"), ("📊 Статистика", "admin:stats")],
            [("💱 Курсы и лимиты", "admin:settings_rates")],
            [("📝 Тексты", "admin:settings_texts"), ("🏦 Реквизиты", "admin:payments")],
            [("👥 Клиенты", "admin:users"), ("💬 Поддержка", "admin:support")],
            [("⭐ Отзывы", "admin:reviews"), ("🤖 Бот", "admin:bot_control")],
            [("📣 Рассылка", "admin:mailing"), ("🛡 Выдать админку", "admin:addadmin")],
            [("🔍 Поиск заявки", "admin:search_order"), ("📩 Сообщение клиенту", "admin:dm_user")],
            [("🏆 Топ клиентов", "admin:top_clients"), ("🆕 Новые пользователи", "admin:recent_users")],
        ]
    )


def admin_back_kb() -> InlineKeyboardMarkup:
    return ikb([[("← В админку", "admin:menu")]])


def admin_orders_menu_kb() -> InlineKeyboardMarkup:
    return ikb(
        [
            [("🆕 Новые", "adm_orders:new"), ("🟡 В работе", "adm_orders:active")],
            [("✅ Завершённые", "adm_orders:completed"), ("⛔ Отказ / отмена", "adm_orders:rejected")],
            [("📚 Все заявки", "adm_orders:all")],
            [("← В админку", "admin:menu")],
        ]
    )


def admin_orders_list_kb(orders, category: str) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = []
    for order in orders:
        status = ORDER_STATUSES.get(order["status"], order["status"])
        order_type = "Покупка" if order["order_type"] == "buy" else "Продажа"
        rows.append([(f"#{order['id']} · {order_type} · {status}", f"adm:order:{order['id']}")])
    rows.append([("🔄 Обновить", f"adm_orders:{category}")])
    rows.append([("← Разделы заявок", "admin:orders")])
    return ikb(rows)


def admin_order_actions_kb(order_id: int, order_type: str) -> InlineKeyboardMarkup:
    first_button = "✅ Оплата получена" if order_type == "buy" else "🤝 Принять в работу"
    first_status = "paid" if order_type == "buy" else "in_progress"
    complete_button = "💎 Выдал голду / закрыть" if order_type == "buy" else "💸 Выплатил / закрыть"
    return ikb(
        [
            [(first_button, f"adm:setstatus:{order_id}:{first_status}")],
            [("🟡 В работе", f"adm:setstatus:{order_id}:in_progress"), (complete_button, f"adm:setstatus:{order_id}:completed")],
            [("⛔ Отклонить", f"adm:setstatus:{order_id}:rejected"), ("✖️ Отменить", f"adm:setstatus:{order_id}:cancelled")],
            [("💬 Написать клиенту", f"adm:msg:{order_id}")],
            [("🔁 Сменить статус", f"adm:chstatus:{order_id}")],
            [("← К списку", "admin:orders")],
        ]
    )


def admin_statuses_kb(order_id: int) -> InlineKeyboardMarkup:
    rows = [[(name, f"adm:setstatus:{order_id}:{status}")] for status, name in ORDER_STATUSES.items()]
    rows.append([("← Вернуться к заявке", f"adm:order:{order_id}")])
    return ikb(rows)


def settings_kb(section: str = "rates") -> InlineKeyboardMarkup:
    keys = NUMERIC_SETTINGS if section == "rates" else TEXT_SETTINGS
    rows = [[(f"✏️ {SETTING_TITLES.get(key, key)}", f"settings:set:{key}")] for key in keys]
    if section == "rates":
        rows.append([("📝 Тексты и контакты", "admin:settings_texts")])
    else:
        rows.append([("💱 Курсы и лимиты", "admin:settings_rates")])
    rows.append([("← В админку", "admin:menu")])
    return ikb(rows)


def payments_list_kb(methods) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = [[("➕ Добавить реквизиты", "pay:add")]]
    for method in methods:
        status = "✅" if method["is_active"] else "⛔"
        title = method["title"]
        rows.append([(f"{status} #{method['id']} · {title}", f"pay:view:{method['id']}")])
    rows.append([("← В админку", "admin:menu")])
    return ikb(rows)


def payment_detail_kb(method_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_text = "⛔ Выключить" if is_active else "✅ Включить"
    return ikb(
        [
            [(toggle_text, f"pay:toggle:{method_id}")],
            [("Название", f"pay:edit:{method_id}:title"), ("Описание", f"pay:edit:{method_id}:bank_name")],
            [("Ссылка / карта", f"pay:edit:{method_id}:card_number"), ("СБП / телефон", f"pay:edit:{method_id}:phone_number")],
            [("Получатель", f"pay:edit:{method_id}:recipient_name"), ("Комментарий", f"pay:edit:{method_id}:comment")],
            [("🗑 Удалить", f"pay:delete:{method_id}")],
            [("← К реквизитам", "admin:payments")],
        ]
    )


def users_menu_kb() -> InlineKeyboardMarkup:
    return ikb(
        [
            [("🔎 Найти клиента", "admin:users_search")],
            [("🛡 Выдать админку", "admin:addadmin")],
            [("← В админку", "admin:menu")],
        ]
    )


def users_search_results_kb(users) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = []
    for user in users:
        username = f"@{user['username']}" if user["username"] else user["first_name"] or "без имени"
        rows.append([(f"{username} · {user['telegram_id']}", f"adm:user:{user['id']}")])
    rows.append([("← К клиентам", "admin:users")])
    return ikb(rows)


def user_admin_actions_kb(user_id: int, is_banned: bool, is_admin: bool) -> InlineKeyboardMarkup:
    ban_text = "✅ Разблокировать" if is_banned else "⛔ Заблокировать"
    ban_value = "0" if is_banned else "1"
    admin_text = "🧹 Забрать админку" if is_admin else "🛡 Сделать админом"
    admin_value = "0" if is_admin else "1"
    return ikb(
        [
            [(ban_text, f"adm:userban:{user_id}:{ban_value}"), (admin_text, f"adm:useradmin:{user_id}:{admin_value}")],
            [("💰 Изменить баланс", f"adm:userbalance:{user_id}"), ("📝 Заметка", f"adm:usernote:{user_id}")],
            [("📦 Заявки клиента", f"adm:userorders:{user_id}")],
            [("← К клиентам", "admin:users")],
        ]
    )


def mailing_confirm_kb() -> InlineKeyboardMarkup:
    return ikb(
        [
            [("🚀 Запустить рассылку", "mail:confirm")],
            [("✖️ Отменить", "admin:menu")],
        ]
    )


def support_ticket_admin_kb(ticket_id: int) -> InlineKeyboardMarkup:
    return ikb(
        [
            [("💬 Ответить клиенту", f"adm:ticketreply:{ticket_id}")],
            [("📚 Все обращения", "admin:support")],
        ]
    )


def support_tickets_list_kb(tickets, category: str = "open") -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = []
    for ticket in tickets:
        username = f"@{ticket['username']}" if ticket["username"] else ticket["first_name"] or "без username"
        status = "Открыто" if ticket["status"] == "open" else "Отвечено"
        rows.append([(f"#{ticket['id']} · {status} · {username}", f"adm:support_ticket:{ticket['id']}")])
    rows.append([("🟢 Открытые", "admin:support:open"), ("✅ Отвеченные", "admin:support:answered")])
    rows.append([("📚 Все", "admin:support:all"), ("🔄 Обновить", f"admin:support:{category}")])
    rows.append([("← В админку", "admin:menu")])
    return ikb(rows)


def admin_topups_menu_kb() -> InlineKeyboardMarkup:
    return ikb(
        [
            [("🟡 На проверке", "adm_topups:waiting_payment")],
            [("✅ Зачисленные", "adm_topups:completed"), ("⛔ Отклонённые", "adm_topups:rejected")],
            [("📚 Все", "adm_topups:all")],
            [("← В админку", "admin:menu")],
        ]
    )


def admin_topups_list_kb(topups, category: str) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = []
    for topup in topups:
        status = TOPUP_STATUSES.get(topup["status"], topup["status"])
        username = f"@{topup['username']}" if topup["username"] else topup["first_name"] or "клиент"
        rows.append([(f"#{topup['id']} · {topup['amount']} ₽ · {status} · {username}", f"adm:topup:{topup['id']}")])
    rows.append([("🔄 Обновить", f"adm_topups:{category}")])
    rows.append([("← Раздел пополнений", "admin:topups")])
    return ikb(rows)


def admin_topup_actions_kb(topup_id: int, status: str) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = []
    if status == "waiting_payment":
        rows.append([("✅ Зачислить", f"adm:topupstatus:{topup_id}:completed")])
        rows.append([("⛔ Отклонить", f"adm:topupstatus:{topup_id}:rejected")])
    rows.append([("← К пополнениям", "admin:topups")])
    return ikb(rows)


def admin_promos_menu_kb() -> InlineKeyboardMarkup:
    return ikb(
        [
            [("🎲 Уникальный одноразовый", "promo_admin:create_unique")],
            [("✍️ Обычный промокод", "promo_admin:create_regular")],
            [("📚 Список промокодов", "promo_admin:list")],
            [("← В админку", "admin:menu")],
        ]
    )


def admin_promos_list_kb(promos) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = []
    for promo in promos:
        status = "✅" if promo["is_active"] else "⛔"
        rows.append([(f"{status} {promo['code']} · {promo['amount']} ₽ · {promo['activations_count']}/{promo['max_activations']}", f"promo_admin:view:{promo['id']}")])
    rows.append([("🔄 Обновить", "promo_admin:list")])
    rows.append([("← Промокоды", "admin:promos")])
    return ikb(rows)


def promo_detail_kb(promo_id: int, is_active: bool) -> InlineKeyboardMarkup:
    text = "⛔ Выключить" if is_active else "✅ Включить"
    return ikb(
        [
            [(text, f"promo_admin:toggle:{promo_id}")],
            [("← К списку", "promo_admin:list")],
        ]
    )


def admin_reviews_menu_kb() -> InlineKeyboardMarkup:
    return ikb(
        [
            [("➕ Добавить отзыв", "adm_reviews:add")],
            [("📚 Последние отзывы", "adm_reviews:list")],
            [("← В админку", "admin:menu")],
        ]
    )


def admin_reviews_list_kb(reviews) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = []
    for review in reviews:
        name = "Аноним" if review["is_anonymous"] else review["display_name"]
        rows.append([(f"#{review['id']} · {'⭐' * int(review['rating'])} · {name}", f"adm_reviews:view:{review['id']}")])
    rows.append([("🔄 Обновить", "adm_reviews:list")])
    rows.append([("← Отзывы", "admin:reviews")])
    return ikb(rows)


def admin_review_detail_kb(review_id: int) -> InlineKeyboardMarkup:
    return ikb(
        [
            [("🗑 Удалить отзыв", f"adm_reviews:delete:{review_id}")],
            [("← К отзывам", "adm_reviews:list")],
        ]
    )


def admin_review_rating_kb() -> InlineKeyboardMarkup:
    return ikb(
        [
            [("⭐", "adm_reviews:rating:1"), ("⭐⭐", "adm_reviews:rating:2"), ("⭐⭐⭐", "adm_reviews:rating:3")],
            [("⭐⭐⭐⭐", "adm_reviews:rating:4"), ("⭐⭐⭐⭐⭐", "adm_reviews:rating:5")],
            [("✖️ Отменить", "admin:reviews")],
        ]
    )


def admin_bot_control_kb(enabled: bool) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = []
    if enabled:
        rows.append([("🔴 Отключить бота", "adm_bot:disable")])
    else:
        rows.append([("🟢 Включить бота", "adm_bot:enable")])
        rows.append([("✏️ Изменить причину", "adm_bot:disable")])
    rows.append([("← В админку", "admin:menu")])
    return ikb(rows)
