from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import Config
from database import Database


class BanMiddleware(BaseMiddleware):
    def __init__(self, db: Database, config: Config | None = None) -> None:
        self.db = db
        self.config = config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is not None:
            row = await self.db.get_user_by_tg(tg_user.id)
            is_admin = bool(row and row["is_admin"])
            if self.config and tg_user.id in self.config.admin_ids:
                is_admin = True

            if row and row["is_banned"] and not is_admin:
                if isinstance(event, Message):
                    await event.answer("<b>Доступ ограничен</b>\n\nВаш профиль заблокирован. Для разблокировки обратитесь в поддержку VoxShop.")
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "Профиль заблокирован. Напишите в поддержку VoxShop.",
                        show_alert=True,
                    )
                return None

            if not is_admin:
                enabled = await self.db.get_setting("bot_enabled")
                if str(enabled) == "0":
                    reason = await self.db.get_setting("bot_disabled_reason")
                    text = f"<b>🔴 VoxShop временно отключён</b>\n\nПричина: {reason or 'технические работы'}"
                    if isinstance(event, Message):
                        await event.answer(text)
                    elif isinstance(event, CallbackQuery):
                        await event.answer(f"Бот отключён. Причина: {reason or 'технические работы'}", show_alert=True)
                    return None
        return await handler(event, data)
