import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API credentials (https://my.telegram.org/apps)
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

# Telegram account
PHONE = os.getenv("PHONE", "")
PASSWORD = os.getenv("PASSWORD", "")

# Session file name
SESSION_NAME = "girlfriend_session"

# Chat history settings
HISTORY_FILE = "chat_history.json"
MAX_HISTORY = 30

# Typing simulation
MIN_TYPING_SECONDS = 2
MAX_TYPING_SECONDS = 6

# Reply only to private messages (not groups/channels)
PRIVATE_ONLY = True

# Whitelist of user IDs to respond to (empty = respond to everyone)
ALLOWED_USERS_RAW = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS = (
    [int(uid.strip()) for uid in ALLOWED_USERS_RAW.split(",") if uid.strip()]
    if ALLOWED_USERS_RAW
    else []
)

# OpenAI-compatible API settings
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.freetheai.xyz/v1")
API_KEY = os.getenv("API_KEY", "")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o")

# Max retries when API fails
GPT_MAX_RETRIES = 3
