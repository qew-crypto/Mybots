import logging
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.config import ADMIN_IDS
from bot.database import (
    get_stats, get_all_users, get_pending_withdrawals, get_withdrawal,
    update_withdrawal_status, get_active_deals, get_all_deals,
    ban_user, unban_user, get_user, get_logs, get_all_user_ids,
    add_log, set_balance, set_setting, get_setting,
)
from bot.keyboards import (
    admin_menu_kb, admin_back_kb, withdrawal_action_kb,
    broadcast_confirm_kb, cancel_kb,
)

router = Router()
logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class AdminStates(StatesGroup):
    broadcast_text = State()
    ban_user_id = State()
    unban_user_id = State()
    credit_user_id = State()
    credit_amount = State()
    debit_user_id = State()
    debit_amount = State()
    set_eval_percent = State()
    set_nft_receiver = State()
    set_currency_rate = State()
    msg_to_user_id = State()
    msg_to_user_text = State()


def _fmt_date(ts: float) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M")


async def _show_admin_panel(target, edit: bool = True):
    stats = await get_stats()
    text = (
        "◈ <b>Админ-панель</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Пользователей: <b>{stats['users_count']}</b>\n"
        f"📊 Активных сделок: <b>{stats['active_deals']}</b>\n"
        f"📨 Заявок на вывод: <b>{stats['pending_withdrawals']}</b>\n"
        f"💰 Оборот: <b>{stats['total_volume']:.2f} ₽</b>"
    )
    if edit and hasattr(target, "message"):
        await target.message.edit_text(text, reply_markup=admin_menu_kb(), parse_mode="HTML")
    elif isinstance(target, Message):
        await target.answer(text, reply_markup=admin_menu_kb(), parse_mode="HTML")
    else:
        await target.message.edit_text(text, reply_markup=admin_menu_kb(), parse_mode="HTML")


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await _show_admin_panel(message, edit=False)


@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await state.clear()
    await _show_admin_panel(callback)
    await callback.answer()


# ─── Users ───
@router.callback_query(F.data == "adm_users")
async def cb_adm_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    users = await get_all_users(limit=20)
    if not users:
        await callback.message.edit_text("Пользователей нет.", reply_markup=admin_back_kb(), parse_mode="HTML")
        await callback.answer()
        return

    lines = ["◈ <b>Пользователи</b>\n━━━━━━━━━━━━━━━━━━━\n"]
    for u in users:
        ban_mark = " 🚫" if u["is_banned"] else ""
        lines.append(
            f"ID: <code>{u['user_id']}</code> | @{u['username'] or '—'} | "
            f"💰 {u['balance']:.2f}₽ | 📦 {u['sold_count']}{ban_mark}"
        )

    await callback.message.edit_text("\n".join(lines), reply_markup=admin_back_kb(), parse_mode="HTML")
    await callback.answer()


# ─── Withdrawals ───
@router.callback_query(F.data == "adm_withdrawals")
async def cb_adm_withdrawals(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    withdrawals = await get_pending_withdrawals()
    if not withdrawals:
        await callback.message.edit_text(
            "📨 Нет активных заявок на вывод.", reply_markup=admin_back_kb(), parse_mode="HTML"
        )
        await callback.answer()
        return

    for w in withdrawals[:5]:
        text = (
            f"◈ <b>Заявка #{w['id']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 @{w['username'] or w['user_id']}\n"
            f"💰 Сумма: <b>{w['amount']:.2f} ₽</b>\n"
            f"📱 Способ: {w['method']}\n"
            f"📝 Реквизиты: <code>{w['details']}</code>\n"
            f"📅 Дата: {_fmt_date(w['created_at'])}\n"
            f"📊 Статус: {w['status']}"
        )
        await callback.message.answer(text, reply_markup=withdrawal_action_kb(w["id"]), parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data.startswith("adm_wd_approve:"))
async def cb_approve_withdrawal(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    wd_id = int(callback.data.split(":")[1])
    wd = await get_withdrawal(wd_id)
    if not wd:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    await update_withdrawal_status(wd_id, "paid")
    await add_log(callback.from_user.id, "withdrawal_approved", f"#{wd_id}")

    await callback.message.edit_text(
        f"✅ Заявка #{wd_id} — выплачено.\nСумма: {wd['amount']:.2f} ₽",
        parse_mode="HTML",
    )

    try:
        await bot.send_message(
            wd["user_id"],
            f"💰 Выплата на сумму <b>{wd['amount']:.2f} ₽</b> выполнена.\n"
            f"Способ: {wd['method']}",
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("adm_wd_reject:"))
async def cb_reject_withdrawal(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    wd_id = int(callback.data.split(":")[1])
    wd = await get_withdrawal(wd_id)
    if not wd:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    await update_withdrawal_status(wd_id, "rejected")
    await add_log(callback.from_user.id, "withdrawal_rejected", f"#{wd_id}")

    from bot.database import update_balance
    await update_balance(wd["user_id"], wd["amount"])

    await callback.message.edit_text(
        f"❌ Заявка #{wd_id} — отклонена.\nБаланс возвращён пользователю.",
        parse_mode="HTML",
    )

    try:
        await bot.send_message(
            wd["user_id"],
            f"❌ Заявка на выплату <b>{wd['amount']:.2f} ₽</b> отклонена.\n"
            f"Средства возвращены на баланс.",
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("adm_wd_msg:"))
async def cb_msg_withdrawal_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    wd_id = int(callback.data.split(":")[1])
    wd = await get_withdrawal(wd_id)
    if not wd:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    await state.set_state(AdminStates.msg_to_user_text)
    await state.update_data(target_user_id=wd["user_id"])
    await callback.message.edit_text(
        f"Введите сообщение для пользователя {wd['user_id']}:",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.msg_to_user_text)
async def process_msg_to_user(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    target_id = data.get("target_user_id")
    if not target_id:
        await state.clear()
        return

    try:
        await bot.send_message(target_id, f"💬 Сообщение от администрации:\n\n{message.text}")
        await message.answer("✅ Сообщение отправлено.", reply_markup=admin_back_kb())
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить: {e}", reply_markup=admin_back_kb())
    await state.clear()


# ─── Deals ───
@router.callback_query(F.data == "adm_deals")
async def cb_adm_deals(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    deals = await get_all_deals(limit=20)
    if not deals:
        await callback.message.edit_text("Сделок нет.", reply_markup=admin_back_kb(), parse_mode="HTML")
        await callback.answer()
        return

    status_map = {
        "awaiting_transfer": "⏳",
        "checking": "🔄",
        "completed": "✅",
        "cancelled": "❌",
        "error": "⚠️",
    }

    lines = ["◈ <b>Сделки</b>\n━━━━━━━━━━━━━━━━━━━\n"]
    for d in deals:
        st = status_map.get(d["status"], d["status"])
        lines.append(
            f"#{d['id']} | @{d.get('username', '—')} | {d['nft_name']} | "
            f"{d['price_rub']:.2f}₽ | {st}"
        )

    await callback.message.edit_text("\n".join(lines), reply_markup=admin_back_kb(), parse_mode="HTML")
    await callback.answer()


# ─── Broadcast ───
@router.callback_query(F.data == "adm_broadcast")
async def cb_adm_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.broadcast_text)
    await callback.message.edit_text(
        "📢 Введите текст рассылки:", reply_markup=cancel_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.broadcast_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = message.text or ""
    await state.update_data(broadcast_text=text)

    preview = (
        "◈ <b>Предпросмотр рассылки</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"{text}"
    )
    await message.answer(preview, reply_markup=broadcast_confirm_kb(), parse_mode="HTML")


@router.callback_query(F.data == "adm_broadcast_send")
async def cb_broadcast_send(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    if not text:
        await callback.answer("Текст пуст.", show_alert=True)
        return

    user_ids = await get_all_user_ids()
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1

    await add_log(callback.from_user.id, "broadcast", f"Sent: {sent}, Failed: {failed}")
    await state.clear()

    await callback.message.edit_text(
        f"✅ Рассылка завершена.\nОтправлено: {sent}\nОшибки: {failed}",
        reply_markup=admin_back_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Bans ───
@router.callback_query(F.data == "adm_bans")
async def cb_adm_bans(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Забанить", callback_data="adm_ban_start")],
        [InlineKeyboardButton(text="✅ Разбанить", callback_data="adm_unban_start")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")],
    ])
    await callback.message.edit_text(
        "◈ <b>Управление банами</b>\n━━━━━━━━━━━━━━━━━━━\n\nВыберите действие:",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "adm_ban_start")
async def cb_ban_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.ban_user_id)
    await callback.message.edit_text(
        "Введите ID пользователя для бана:", reply_markup=cancel_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.ban_user_id)
async def process_ban_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("❌ Введите корректный ID.")
        return

    user = await get_user(uid)
    if not user:
        await message.answer("❌ Пользователь не найден.", reply_markup=admin_back_kb())
        await state.clear()
        return

    await ban_user(uid)
    await add_log(message.from_user.id, "ban_user", str(uid))
    await state.clear()

    await message.answer(
        f"🚫 Пользователь {uid} заблокирован.", reply_markup=admin_back_kb()
    )


@router.callback_query(F.data == "adm_unban_start")
async def cb_unban_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.unban_user_id)
    await callback.message.edit_text(
        "Введите ID пользователя для разбана:", reply_markup=cancel_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.unban_user_id)
async def process_unban_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("❌ Введите корректный ID.")
        return

    await unban_user(uid)
    await add_log(message.from_user.id, "unban_user", str(uid))
    await state.clear()

    await message.answer(
        f"✅ Пользователь {uid} разблокирован.", reply_markup=admin_back_kb()
    )


# ─── Settings ───
@router.callback_query(F.data == "adm_settings")
async def cb_adm_settings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    eval_pct = await get_setting("eval_percent", "85")
    receiver = await get_setting("nft_receiver", "VoxManagerNFT")
    custom_rate = await get_setting("custom_ton_rub_rate", "")

    text = (
        "◈ <b>Настройки</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Процент оценки: <b>{eval_pct}%</b>\n"
        f"📥 Получатель NFT: <b>@{receiver}</b>\n"
        f"💱 Курс TON/RUB: <b>{'авто' if not custom_rate else custom_rate + ' ₽'}</b>"
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Процент оценки", callback_data="adm_set_eval")],
        [InlineKeyboardButton(text="📥 Получатель NFT", callback_data="adm_set_receiver")],
        [InlineKeyboardButton(text="💱 Курс валют", callback_data="adm_set_rate")],
        [InlineKeyboardButton(text="💳 Начислить баланс", callback_data="adm_credit_start")],
        [InlineKeyboardButton(text="💸 Списать баланс", callback_data="adm_debit_start")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "adm_set_eval")
async def cb_set_eval(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.set_eval_percent)
    await callback.message.edit_text(
        "Введите новый процент оценки (1-100):", reply_markup=cancel_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.set_eval_percent)
async def process_set_eval(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        val = float(message.text.strip())
        if not (1 <= val <= 100):
            raise ValueError
    except (ValueError, TypeError):
        await message.answer("❌ Введите число от 1 до 100.")
        return

    await set_setting("eval_percent", str(val))
    await add_log(message.from_user.id, "setting_changed", f"eval_percent={val}")
    await state.clear()
    await message.answer(f"✅ Процент оценки: {val}%", reply_markup=admin_back_kb())


@router.callback_query(F.data == "adm_set_receiver")
async def cb_set_receiver(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.set_nft_receiver)
    await callback.message.edit_text(
        "Введите username аккаунта-получателя NFT (без @):",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.set_nft_receiver)
async def process_set_receiver(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    val = message.text.strip().lstrip("@")
    if not val:
        await message.answer("❌ Введите корректный username.")
        return

    await set_setting("nft_receiver", val)
    await add_log(message.from_user.id, "setting_changed", f"nft_receiver={val}")
    await state.clear()
    await message.answer(f"✅ Получатель NFT: @{val}", reply_markup=admin_back_kb())


@router.callback_query(F.data == "adm_set_rate")
async def cb_set_rate(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.set_currency_rate)
    await callback.message.edit_text(
        "Введите фиксированный курс TON/RUB\n(или 0 для автокурса):",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.set_currency_rate)
async def process_set_rate(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        val = float(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("❌ Введите число.")
        return

    if val <= 0:
        await set_setting("custom_ton_rub_rate", "")
        await state.clear()
        await message.answer("✅ Установлен автоматический курс.", reply_markup=admin_back_kb())
    else:
        await set_setting("custom_ton_rub_rate", str(val))
        await state.clear()
        await message.answer(f"✅ Курс TON/RUB: {val} ₽", reply_markup=admin_back_kb())

    await add_log(message.from_user.id, "setting_changed", f"ton_rub_rate={val}")


# ─── Credit / Debit ───
@router.callback_query(F.data == "adm_credit_start")
async def cb_credit_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.credit_user_id)
    await callback.message.edit_text(
        "Введите ID пользователя для начисления:", reply_markup=cancel_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.credit_user_id)
async def process_credit_user_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("❌ Введите корректный ID.")
        return

    user = await get_user(uid)
    if not user:
        await message.answer("❌ Пользователь не найден.", reply_markup=admin_back_kb())
        await state.clear()
        return

    await state.update_data(target_user_id=uid)
    await state.set_state(AdminStates.credit_amount)
    await message.answer(f"Текущий баланс: {user['balance']:.2f} ₽\nВведите сумму начисления:")


@router.message(AdminStates.credit_amount)
async def process_credit_amount(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    uid = data["target_user_id"]
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer("❌ Введите положительное число.")
        return

    from bot.database import update_balance
    await update_balance(uid, amount)
    await add_log(message.from_user.id, "admin_credit", f"User {uid} +{amount}₽")
    await state.clear()

    await message.answer(f"✅ Начислено {amount:.2f} ₽ пользователю {uid}.", reply_markup=admin_back_kb())
    try:
        await bot.send_message(uid, f"💰 На ваш баланс начислено <b>{amount:.2f} ₽</b>.", parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data == "adm_debit_start")
async def cb_debit_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.debit_user_id)
    await callback.message.edit_text(
        "Введите ID пользователя для списания:", reply_markup=cancel_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.debit_user_id)
async def process_debit_user_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("❌ Введите корректный ID.")
        return

    user = await get_user(uid)
    if not user:
        await message.answer("❌ Пользователь не найден.", reply_markup=admin_back_kb())
        await state.clear()
        return

    await state.update_data(target_user_id=uid)
    await state.set_state(AdminStates.debit_amount)
    await message.answer(f"Текущий баланс: {user['balance']:.2f} ₽\nВведите сумму списания:")


@router.message(AdminStates.debit_amount)
async def process_debit_amount(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    uid = data["target_user_id"]
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer("❌ Введите положительное число.")
        return

    user = await get_user(uid)
    new_balance = max(0, (user["balance"] if user else 0) - amount)
    await set_balance(uid, new_balance)
    await add_log(message.from_user.id, "admin_debit", f"User {uid} -{amount}₽")
    await state.clear()

    await message.answer(
        f"✅ Списано {amount:.2f} ₽ у пользователя {uid}.\nНовый баланс: {new_balance:.2f} ₽",
        reply_markup=admin_back_kb(),
    )


# ─── Logs ───
@router.callback_query(F.data == "adm_logs")
async def cb_adm_logs(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    logs = await get_logs(limit=20)
    if not logs:
        await callback.message.edit_text("Логов нет.", reply_markup=admin_back_kb(), parse_mode="HTML")
        await callback.answer()
        return

    lines = ["◈ <b>Последние логи</b>\n━━━━━━━━━━━━━━━━━━━\n"]
    for log in logs:
        dt = _fmt_date(log["created_at"])
        lines.append(f"<code>{dt}</code> | {log['user_id']} | {log['action']}")
        if log["details"]:
            lines.append(f"  ↳ {log['details']}")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n..."

    await callback.message.edit_text(text, reply_markup=admin_back_kb(), parse_mode="HTML")
    await callback.answer()
