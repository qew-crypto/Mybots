import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import BOT_TOKEN
from bot.database import init_db
from bot.handlers import start, sell, profile, reviews, support, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Create .env file with BOT_TOKEN=your_token")
        return

    await init_db()
    logger.info("Database initialized")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(sell.router)
    dp.include_router(profile.router)
    dp.include_router(reviews.router)
    dp.include_router(support.router)
    dp.include_router(admin.router)

    logger.info("Vox NFT Market bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
