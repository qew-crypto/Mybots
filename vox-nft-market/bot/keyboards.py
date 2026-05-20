from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Продать NFT", callback_data="sell_nft")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="⭐ Отзывы", callback_data="reviews")],
        [InlineKeyboardButton(text="💬 Поддержка", callback_data="support")],
    ])


def sell_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_sell")],
    ])


def deal_actions_kb(deal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить передачу", callback_data=f"check_transfer:{deal_id}")],
        [InlineKeyboardButton(text="❌ Отменить продажу", callback_data=f"cancel_deal:{deal_id}")],
    ])


def deal_confirmed_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Перейти в профиль", callback_data="profile")],
        [InlineKeyboardButton(text="💎 Продать ещё NFT", callback_data="sell_nft")],
    ])


def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Вывести", callback_data="withdraw")],
        [InlineKeyboardButton(text="📋 История продаж", callback_data="deal_history")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
    ])


def withdraw_methods_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 СБП", callback_data="withdraw_method:sbp")],
        [InlineKeyboardButton(text="💳 Банковская карта", callback_data="withdraw_method:card")],
        [InlineKeyboardButton(text="💵 USDT", callback_data="withdraw_method:usdt")],
        [InlineKeyboardButton(text="💠 TON", callback_data="withdraw_method:ton")],
        [InlineKeyboardButton(text="🌍 Зарубежная карта", callback_data="withdraw_method:intl_card")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="profile")],
    ])


def back_to_profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="profile")],
    ])


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ])


def reviews_kb(has_completed_deal: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    if has_completed_deal:
        buttons.append([InlineKeyboardButton(text="✏️ Оставить отзыв", callback_data="leave_review")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def review_rating_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 ⭐", callback_data="rate:1"),
            InlineKeyboardButton(text="2 ⭐", callback_data="rate:2"),
            InlineKeyboardButton(text="3 ⭐", callback_data="rate:3"),
            InlineKeyboardButton(text="4 ⭐", callback_data="rate:4"),
            InlineKeyboardButton(text="5 ⭐", callback_data="rate:5"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="reviews")],
    ])


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="adm_users"),
            InlineKeyboardButton(text="📨 Заявки", callback_data="adm_withdrawals"),
        ],
        [
            InlineKeyboardButton(text="📊 Сделки", callback_data="adm_deals"),
            InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast"),
        ],
        [
            InlineKeyboardButton(text="🚫 Баны", callback_data="adm_bans"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="adm_settings"),
        ],
        [InlineKeyboardButton(text="📜 Логи", callback_data="adm_logs")],
    ])


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в админку", callback_data="admin_panel")],
    ])


def withdrawal_action_kb(withdrawal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выплачено", callback_data=f"adm_wd_approve:{withdrawal_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_wd_reject:{withdrawal_id}"),
        ],
        [InlineKeyboardButton(text="💬 Написать", callback_data=f"adm_wd_msg:{withdrawal_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="adm_withdrawals")],
    ])


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Отправить всем", callback_data="adm_broadcast_send")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")],
    ])


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")],
    ])
