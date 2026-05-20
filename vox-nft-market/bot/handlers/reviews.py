from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.database import (
    get_reviews, get_reviews_stats, add_review, add_log,
    get_user_completed_deals_count,
)
from bot.keyboards import reviews_kb, review_rating_kb, back_to_menu_kb

router = Router()

DEMO_REVIEWS = [
    {"text": "Продал подарок быстро, деньги пришли без задержек.", "rating": 5},
    {"text": "Удобный бот, всё понятно с первого раза.", "rating": 5},
    {"text": "Оценка нормальная, вывод занял пару минут.", "rating": 4},
    {"text": "Сначала сомневался, но сделка прошла успешно.", "rating": 5},
    {"text": "Интерфейс красивый, пользоваться приятно.", "rating": 5},
    {"text": "Быстрая проверка NFT и понятный профиль.", "rating": 4},
    {"text": "Продал несколько подарков, баланс начислился сразу.", "rating": 5},
    {"text": "Выплата пришла на карту, всё ок.", "rating": 4},
    {"text": "Хороший сервис для быстрой продажи NFT.", "rating": 5},
    {"text": "Удобно, что бот сам проверяет передачу.", "rating": 5},
]


class ReviewStates(StatesGroup):
    waiting_rating = State()
    waiting_text = State()


def _stars(rating: int) -> str:
    return "⭐" * rating


async def _build_reviews_text() -> str:
    stats = await get_reviews_stats()
    real_reviews = await get_reviews(limit=10)

    total_count = stats["count"]
    avg_rating = stats["avg_rating"]

    if total_count == 0:
        display_reviews = DEMO_REVIEWS[:5]
        note = "\n<i>📌 Демонстрационные отзывы</i>\n"
        total_text = f"{len(DEMO_REVIEWS)}"
        avg_text = "4.8"
    else:
        display_reviews = []
        for r in real_reviews:
            display_reviews.append({
                "text": r["text"],
                "rating": r["rating"],
                "date": datetime.fromtimestamp(r["created_at"]).strftime("%d.%m.%Y"),
            })
        note = ""
        total_text = str(total_count)
        avg_text = str(avg_rating)

    lines = [
        "◈ <b>Отзывы пользователей</b>",
        "━━━━━━━━━━━━━━━━━━━\n",
        f"Общая оценка: <b>{avg_text} / 5</b>",
        f"Всего отзывов: <b>{total_text}</b>",
        note,
        "Последние отзывы:\n",
    ]

    for r in display_reviews:
        date_str = r.get("date", "")
        stars = _stars(r["rating"])
        lines.append(f"  {stars}")
        lines.append(f"  <i>«{r['text']}»</i>")
        lines.append(f"  — Анонимный пользователь")
        if date_str:
            lines.append(f"  {date_str}")
        lines.append("")

    return "\n".join(lines)


@router.callback_query(F.data == "reviews")
async def cb_reviews(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = await _build_reviews_text()
    has_deals = (await get_user_completed_deals_count(callback.from_user.id)) > 0
    await callback.message.edit_text(text, reply_markup=reviews_kb(has_deals), parse_mode="HTML")
    await callback.answer()


@router.message(Command("reviews"))
async def cmd_reviews(message: Message, state: FSMContext):
    await state.clear()
    text = await _build_reviews_text()
    has_deals = (await get_user_completed_deals_count(message.from_user.id)) > 0
    await message.answer(text, reply_markup=reviews_kb(has_deals), parse_mode="HTML")


@router.callback_query(F.data == "leave_review")
async def cb_leave_review(callback: CallbackQuery, state: FSMContext):
    has_deals = (await get_user_completed_deals_count(callback.from_user.id)) > 0
    if not has_deals:
        await callback.answer("Оставить отзыв можно после завершённой сделки.", show_alert=True)
        return

    await state.set_state(ReviewStates.waiting_rating)
    await callback.message.edit_text(
        "◈ <b>Оставить отзыв</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Оцените сервис:",
        reply_markup=review_rating_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rate:"), ReviewStates.waiting_rating)
async def cb_rate(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split(":")[1])
    await state.update_data(rating=rating)
    await state.set_state(ReviewStates.waiting_text)

    await callback.message.edit_text(
        f"◈ Оценка: {_stars(rating)}\n\n"
        f"Напишите ваш отзыв:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ReviewStates.waiting_text)
async def process_review_text(message: Message, state: FSMContext):
    data = await state.get_data()
    rating = data.get("rating", 5)
    text = message.text or ""

    if len(text.strip()) < 3:
        await message.answer("Напишите хотя бы несколько слов.")
        return

    if len(text) > 500:
        text = text[:500]

    await add_review(message.from_user.id, rating, text.strip())
    await add_log(message.from_user.id, "review_added", f"{rating}⭐")
    await state.clear()

    await message.answer(
        "✅ Спасибо за ваш отзыв!",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
