import json
import os
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL, HISTORY_FILE, MAX_HISTORY
from prompt import SYSTEM_PROMPT


client = OpenAI(api_key=OPENAI_API_KEY)


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


def get_response(user_id: int, message: str) -> str | None:
    try:
        add_message(user_id, "user", message)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(get_user_history(user_id))

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=1.0,
            max_tokens=300,
            presence_penalty=0.6,
            frequency_penalty=0.3,
        )

        reply = response.choices[0].message.content
        if reply:
            add_message(user_id, "assistant", reply)
            return reply
        return None

    except Exception as e:
        print(f"[GPT ERROR] {e}")
        return None
