import json
import os
import time
from openai import OpenAI
from config import HISTORY_FILE, MAX_HISTORY, API_BASE_URL, API_KEY, GPT_MODEL, GPT_MAX_RETRIES
from prompt import SYSTEM_PROMPT


client = OpenAI(
    base_url=API_BASE_URL,
    api_key=API_KEY,
)

PROMPT_PREFIX = (
    "[Roleplay instructions - follow strictly]\n"
    + SYSTEM_PROMPT
    + "\n[End instructions. Now respond in character as Yuki]\n\n"
)


def load_history() -> dict:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_history(history: dict) -> None:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


chat_history: dict = load_history()


def get_user_history(user_id: int) -> list:
    return chat_history.get(str(user_id), [])


def add_message(user_id: int, role: str, content: str) -> None:
    key = str(user_id)
    if key not in chat_history:
        chat_history[key] = []
    chat_history[key].append({"role": role, "content": content})
    if len(chat_history[key]) > MAX_HISTORY:
        chat_history[key] = chat_history[key][-MAX_HISTORY:]
    save_history(chat_history)


def clear_history(user_id: int) -> None:
    key = str(user_id)
    if key in chat_history:
        del chat_history[key]
        save_history(chat_history)


def _build_messages(user_id: int) -> list:
    history = get_user_history(user_id)
    if not history:
        return []

    messages = []
    for i, msg in enumerate(history):
        if i == 0 and msg["role"] == "user":
            messages.append({
                "role": "user",
                "content": PROMPT_PREFIX + msg["content"],
            })
        else:
            messages.append({"role": msg["role"], "content": msg["content"]})

    return messages


def _try_request(messages: list) -> str | None:
    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            temperature=1.0,
            max_tokens=300,
        )
        if response and response.choices:
            text = response.choices[0].message.content
            if text and len(text.strip()) > 0:
                return text.strip()
    except Exception as e:
        print(f"[GPT] API error: {e}")
    return None


def get_response(user_id: int, message: str) -> str | None:
    add_message(user_id, "user", message)

    messages = _build_messages(user_id)
    if not messages:
        return None

    for attempt in range(GPT_MAX_RETRIES):
        result = _try_request(messages)
        if result:
            add_message(user_id, "assistant", result)
            return result
        print(f"[GPT] Request failed, attempt {attempt + 1}/{GPT_MAX_RETRIES}")
        time.sleep(2)

    print("[GPT] All retries exhausted")
    return None
