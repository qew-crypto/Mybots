from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from database import Database
from handlers_admin import router as admin_router
from handlers_user import router as user_router
from logger import setup_logging
from middlewares import BanMiddleware

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()
    config = load_config()

    db = Database(config.db_path)
    await db.connect()
    await db.init()
    await db.ensure_admin_ids(config.admin_ids)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp["db"] = db
    dp["config"] = config

    dp.message.middleware(BanMiddleware(db, config))
    dp.callback_query.middleware(BanMiddleware(db, config))

    dp.include_router(user_router)
    dp.include_router(admin_router)

    @dp.error()
    async def global_error_handler(event: ErrorEvent) -> bool:
        logger.exception("Unhandled update error", exc_info=event.exception)
        return True

    logger.info("Bot started")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
