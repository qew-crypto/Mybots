from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# ==============================
# VoxShop configuration
# ==============================
# .env больше не нужен: все базовые настройки лежат здесь.
# Перед запуском вставь токен бота от BotFather в BOT_TOKEN.
# Рекомендация: не публикуй config.py с реальным токеном в открытом доступе.

BOT_NAME = "VoxShop"
BOT_TOKEN = "PASTE_BOT_TOKEN_HERE"
ADMIN_IDS = [7962973666]
DB_PATH = "voxshop.db"
SUPPORT_CONTACT = "@kawalskuy"

BASE_DIR = Path(__file__).resolve().parent


@dataclass(slots=True)
class Config:
    bot_name: str
    bot_token: str
    admin_ids: list[int]
    db_path: str
    support_contact: str


def _validate_admin_ids(admin_ids: list[int]) -> list[int]:
    result: list[int] = []
    for admin_id in admin_ids:
        if isinstance(admin_id, int) and admin_id > 0:
            result.append(admin_id)
    return sorted(set(result))


def load_config() -> Config:
    token = BOT_TOKEN.strip()
    if not token or token in {"PASTE_BOT_TOKEN_HERE", "CHANGE_ME"}:
        raise RuntimeError(
            "Не указан BOT_TOKEN. Открой config.py и вставь токен бота в переменную BOT_TOKEN."
        )

    return Config(
        bot_name=BOT_NAME.strip() or "VoxShop",
        bot_token=token,
        admin_ids=_validate_admin_ids(ADMIN_IDS),
        db_path=str(BASE_DIR / (DB_PATH.strip() or "voxshop.db")),
        support_contact=SUPPORT_CONTACT.strip() or "@kawalskuy",
    )
