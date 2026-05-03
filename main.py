import asyncio
import sys
from config import API_ID, API_HASH, PHONE, OPENAI_API_KEY


def check_config() -> bool:
    ok = True
    if not API_ID:
        print("[ERROR] API_ID не задан. Получи его на https://my.telegram.org/apps")
        ok = False
    if not API_HASH:
        print("[ERROR] API_HASH не задан. Получи его на https://my.telegram.org/apps")
        ok = False
    if not PHONE:
        print("[ERROR] PHONE не задан. Укажи номер телефона в .env")
        ok = False
    if not OPENAI_API_KEY:
        print("[ERROR] OPENAI_API_KEY не задан. Получи ключ на https://platform.openai.com")
        ok = False
    return ok


def main() -> None:
    print("=" * 50)
    print("   Telegram AI Girlfriend Bot (Userbot)")
    print("=" * 50)

    if not check_config():
        print("\nЗаполни файл .env и попробуй снова!")
        sys.exit(1)

    from bot import start_bot

    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("\n[BOT] Бот остановлен.")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
