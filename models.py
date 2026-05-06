ORDER_TYPE_NAMES = {
    "buy": "Покупка голды",
    "sell": "Продажа голды",
}

ORDER_STATUSES = {
    "new": "Новая",
    "waiting_payment": "Ожидает проверки",
    "paid": "Оплачена",
    "in_progress": "В работе",
    "completed": "Завершена",
    "rejected": "Отклонена",
    "cancelled": "Отменена",
}

TOPUP_STATUSES = {
    "waiting_payment": "Ожидает проверки",
    "completed": "Зачислено",
    "rejected": "Отклонено",
}

ACTIVE_STATUSES = ("new", "waiting_payment", "paid", "in_progress")
FINAL_STATUSES = ("completed", "rejected", "cancelled")

NUMERIC_SETTINGS = (
    "sell_rate_to_user",
    "buy_rate_from_user",
    "min_buy_gold",
    "min_sell_gold",
    "max_gold",
)

TEXT_SETTINGS = (
    "bot_name",
    "support_contact",
    "welcome_text",
    "after_buy_text",
    "after_sell_text",
    "faq_text",
    "bot_disabled_reason",
)

# При смене версии бот обновляет дефолтные тексты в старой базе,
# чтобы новый дизайн применился без удаления voxshop.db.
UI_TEXT_VERSION = "voxshop-ui-v6"
FORCED_TEXT_SETTING_KEYS = (
    "bot_name",
    "support_contact",
    "welcome_text",
    "after_buy_text",
    "after_sell_text",
    "faq_text",
)

DEFAULT_PAYMENT_METHOD = {
    "title": "DonateAlerts",
    "bank_name": "Все карты + зарубежные платежи",
    "card_number": "https://www.donationalerts.com/r/kaktusik_crypa228",
    "phone_number": None,
    "recipient_name": "VoxShop",
    "comment": "В комментарии к оплате укажите свой Telegram username.",
}

DEFAULT_SETTINGS = {
    # Курс продажи голды пользователям: клиент покупает у бота.
    "sell_rate_to_user": "0.85",
    # Курс покупки голды у пользователей: клиент продаёт боту.
    "buy_rate_from_user": "0.70",
    "min_buy_gold": "10",
    "min_sell_gold": "10",
    "max_gold": "10000",
    "bot_name": "VoxShop",
    "support_contact": "@kawalskuy",
    "welcome_text": (
        "VoxShop — магазин голды Standoff 2.\n"
        "Покупка, продажа, баланс, промокоды и отзывы в одном боте.\n\n"
        "Все заявки проверяются вручную. Мы не просим пароли, коды и доступ к аккаунтам."
    ),
    "after_buy_text": (
        "Заявка отправлена на проверку.\n"
        "Для получения голды напишите в поддержку {support}.\n"
        "Сообщите номер заявки #{order_id}, количество голды и приложите чек/комментарий."
    ),
    "after_sell_text": (
        "Заявка отправлена администратору.\n"
        "Чтобы передать голду и получить выплату, напишите в поддержку {support}.\n"
        "Сообщите номер заявки #{order_id}, количество голды и реквизиты."
    ),
    "faq_text": (
        "Правила VoxShop\n\n"
        "1. Все сделки проходят через заявку и проверяются вручную.\n"
        "2. Покупка: выберите количество, оплатите через DonateAlerts или баланс и отправьте чек.\n"
        "3. Продажа: укажите количество голды и реквизиты для выплаты.\n"
        "4. После создания заявки напишите в поддержку @kawalskuy.\n"
        "5. Баланс пополняется после ручной проверки чека администратором.\n"
        "6. Реферальный бонус: 10% от подтверждённых пополнений приглашённых клиентов.\n"
        "7. Не отправляйте пароли, SMS-коды и данные входа."
    ),
    "ui_text_version": UI_TEXT_VERSION,
    "seed_reviews_done": "0",
    "bot_enabled": "1",
    "bot_disabled_reason": "Технические работы. Бот скоро вернётся.",
}

SETTING_TITLES = {
    "sell_rate_to_user": "Курс продажи клиентам",
    "buy_rate_from_user": "Курс выкупа у клиентов",
    "min_buy_gold": "Минимум для покупки",
    "min_sell_gold": "Минимум для продажи",
    "max_gold": "Максимум в заявке",
    "bot_name": "Название магазина",
    "support_contact": "Контакт поддержки",
    "welcome_text": "Приветствие",
    "after_buy_text": "Текст после покупки",
    "after_sell_text": "Текст после продажи",
    "faq_text": "FAQ / Правила",
    "bot_disabled_reason": "Причина отключения бота",
}

SETTING_HINTS = {
    "sell_rate_to_user": "Например: 0.85 — клиент покупает 1 голду за 0.85 ₽.",
    "buy_rate_from_user": "Например: 0.70 — клиент продаёт 1 голду за 0.70 ₽.",
    "min_buy_gold": "Например: 10",
    "min_sell_gold": "Например: 10",
    "max_gold": "Например: 10000",
    "bot_name": "Например: VoxShop",
    "support_contact": "Например: @kawalskuy",
    "welcome_text": "Можно отправить многострочный текст. HTML использовать не нужно.",
    "after_buy_text": "Можно использовать переменные {support} и {order_id}.",
    "after_sell_text": "Можно использовать переменные {support} и {order_id}.",
    "faq_text": "Можно отправить многострочный текст с правилами и FAQ.",
    "bot_disabled_reason": "Этот текст увидят клиенты, когда магазин выключен.",
}
