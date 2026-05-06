from aiogram.fsm.state import State, StatesGroup


class BuyStates(StatesGroup):
    amount = State()
    receipt = State()


class SellStates(StatesGroup):
    amount = State()
    payment_details = State()


class TopUpStates(StatesGroup):
    amount = State()
    receipt = State()


class PromoStates(StatesGroup):
    code = State()


class ReviewStates(StatesGroup):
    rating = State()
    visibility = State()
    text = State()


class SupportStates(StatesGroup):
    message = State()


class AdminSettingsStates(StatesGroup):
    set_value = State()


class AdminPaymentStates(StatesGroup):
    title = State()
    bank_name = State()
    card_number = State()
    phone_number = State()
    recipient_name = State()
    comment = State()
    edit_value = State()


class AdminOrderStates(StatesGroup):
    message_user = State()


class AdminSupportStates(StatesGroup):
    answer = State()


class AdminUserStates(StatesGroup):
    search = State()
    note = State()
    add_admin = State()
    balance = State()


class AdminMailingStates(StatesGroup):
    content = State()
    preview = State()


class AdminPromoStates(StatesGroup):
    unique_amount = State()
    regular_code = State()
    regular_amount = State()
    regular_limit = State()

class AdminReviewStates(StatesGroup):
    rating = State()
    name = State()
    text = State()

class AdminBotControlStates(StatesGroup):
    disable_reason = State()


class AdminDirectMessageStates(StatesGroup):
    telegram_id = State()
    text = State()


class AdminSearchOrderStates(StatesGroup):
    query = State()
