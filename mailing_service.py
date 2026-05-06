from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from database import Database

logger = logging.getLogger(__name__)


async def run_mailing(
    bot: Bot,
    db: Database,
    *,
    text: str | None,
    photo_file_id: str | None,
) -> tuple[int, int, int]:
    mailing_id = await db.create_mailing(text, photo_file_id)
    users = await db.get_mailing_users()
    sent = 0
    failed = 0

    for user in users:
        try:
            if photo_file_id:
                await bot.send_photo(user["telegram_id"], photo_file_id, caption=text or "", parse_mode=None)
            else:
                await bot.send_message(user["telegram_id"], text or "", parse_mode=None)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
            logger.exception("Failed to send mailing to %s", user["telegram_id"])

    await db.update_mailing_result(mailing_id, sent, failed)
    return mailing_id, sent, failed
