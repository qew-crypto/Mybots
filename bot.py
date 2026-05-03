import asyncio
import random
from telethon import TelegramClient, events, functions
from telethon.tl.functions.messages import ReadHistoryRequest
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


async def mark_read(event) -> None:
    try:
        await client(ReadHistoryRequest(
            peer=await event.get_input_chat(),
            max_id=event.id,
        ))
    except Exception as e:
        print(f"[READ ERROR] {e}")


async def typing_while_generating(chat, future) -> None:
    """Show 'typing...' continuously while GPT generates a response."""
    try:
        while not future.done():
            async with client.action(chat, "typing"):
                await asyncio.sleep(5)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[TYPING ERROR] {e}")


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

    # Mark message as read
    await set_online()
    await mark_read(event)

    # /clear command
    if text.strip().lower() in ("/clear", "/сброс"):
        clear_history(user_id)
        async with client.action(event.chat_id, "typing"):
            await asyncio.sleep(random.uniform(1, 2))
        await event.reply("Хм, о чём мы говорили? Я всё забыла 😅")
        return

    # Small delay before typing starts (like reading the message)
    await asyncio.sleep(random.uniform(0.5, 1.5))

    # Start typing and generate response simultaneously
    loop = asyncio.get_event_loop()
    future = loop.run_in_executor(None, get_response, user_id, text)

    typing_task = asyncio.create_task(
        typing_while_generating(event.chat_id, future)
    )

    reply = await future
    typing_task.cancel()

    if reply:
        # Extra short typing pause for realism after generation
        async with client.action(event.chat_id, "typing"):
            extra = random.uniform(
                MIN_TYPING_SECONDS,
                min(MAX_TYPING_SECONDS, MIN_TYPING_SECONDS + len(reply) / 60),
            )
            await asyncio.sleep(extra)
        await event.reply(reply)
    else:
        async with client.action(event.chat_id, "typing"):
            await asyncio.sleep(random.uniform(1, 2))
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

    asyncio.create_task(keep_online())

    await client.run_until_disconnected()
