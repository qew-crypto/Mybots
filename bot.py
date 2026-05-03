import asyncio
import random
from telethon import TelegramClient, events, functions
from telethon.tl.types import UpdateUserStatus, UserStatusOnline
from config import (
    API_ID,
    API_HASH,
    PHONE,
    PASSWORD,
    SESSION_NAME,
    PRIVATE_ONLY,
    ALLOWED_USERS,
    MIN_TYPING_SECONDS,
    MAX_TYPING_SECONDS,
)
from gpt import get_response, clear_history


client = TelegramClient(SESSION_NAME, API_ID, API_HASH)


async def set_online() -> None:
    try:
        await client(functions.account.UpdateStatusRequest(offline=False))
    except Exception as e:
        print(f"[ONLINE ERROR] {e}")


async def simulate_typing(chat, message: str) -> None:
    length = len(message)
    base = random.uniform(MIN_TYPING_SECONDS, MAX_TYPING_SECONDS)
    extra = min(length / 80, 4)
    duration = base + extra

    async with client.action(chat, "typing"):
        await asyncio.sleep(duration)


async def keep_online() -> None:
    while True:
        await set_online()
        await asyncio.sleep(270)


@client.on(events.NewMessage(incoming=True))
async def handler(event) -> None:
    if event.is_group or event.is_channel:
        if PRIVATE_ONLY:
            return

    sender = await event.get_sender()
    if not sender or sender.bot:
        return

    user_id = sender.id
    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        return

    text = event.raw_text
    if not text:
        return

    # /clear command resets conversation history
    if text.strip().lower() in ("/clear", "/сброс"):
        clear_history(user_id)
        await simulate_typing(event.chat_id, "Хм, о чём мы говорили?")
        await event.reply("Хм, о чём мы говорили? Я всё забыла 😅")
        return

    await set_online()

    reply = get_response(user_id, text)
    if reply:
        await simulate_typing(event.chat_id, reply)
        await event.reply(reply)
    else:
        await simulate_typing(event.chat_id, "Чёт я тупнула")
        await event.reply("Чёт я тупнула, напиши ещё раз 😅")

    await set_online()


async def start_bot() -> None:
    print("[BOT] Подключение к Telegram...")
    await client.start(phone=PHONE, password=PASSWORD)
    me = await client.get_me()
    print(f"[BOT] Вошли как: {me.first_name} (@{me.username})")
    print(f"[BOT] ID: {me.id}")
    print("[BOT] Бот запущен! Ожидаю сообщений...")

    await set_online()

    # Keep-alive task to maintain online status
    asyncio.create_task(keep_online())

    await client.run_until_disconnected()
