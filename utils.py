from __future__ import annotations

import html
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


MONEY_QUANT = Decimal("0.01")
GOLD_QUANT = Decimal("0.01")


def h(value: object) -> str:
    return html.escape("" if value is None else str(value))


def parse_positive_decimal(text: str | None) -> Decimal:
    if text is None:
        raise ValueError("Пустое значение")
    normalized = text.strip().replace(" ", "").replace(",", ".")
    if not normalized:
        raise ValueError("Пустое значение")
    try:
        value = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError("Введите число") from exc
    if value <= 0:
        raise ValueError("Число должно быть больше нуля")
    return value


def to_decimal(value: object, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


def money(value: object) -> Decimal:
    return to_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def gold(value: object) -> Decimal:
    return to_decimal(value).quantize(GOLD_QUANT, rounding=ROUND_HALF_UP)


def fmt_money(value: object) -> str:
    return f"{money(value)} ₽"


def fmt_gold(value: object) -> str:
    d = gold(value)
    if d == d.to_integral():
        return str(d.to_integral())
    return str(d.normalize())


def yes_no(value: object) -> str:
    return "✅ Да" if bool(value) else "— Нет"


def short_text(value: object, limit: int = 80) -> str:
    text = "" if value is None else str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"
