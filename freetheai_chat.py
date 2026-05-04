#!/usr/bin/env python3
"""
FreeTheAi GPT Chat — однофайловый скрипт для общения с AI моделями.

Используй бесплатный API freetheai.xyz для доступа к GPT-5, Claude, Gemini и другим моделям.

Установка:
    pip install requests

Получение API ключа:
    1. Зайди в Discord: https://discord.gg/secrets
    2. Введи команду /signup
    3. Скопируй полученный ключ

Использование:
    python freetheai_chat.py                          # запуск (ключ из .env или ввод вручную)
    FREETHEAI_KEY=sta_xxx python freetheai_chat.py    # ключ через переменную окружения

Команды в чате:
    /model           — выбрать модель
    /models          — показать все доступные модели
    /clear           — очистить историю диалога
    /system <текст>  — задать системный промт
    /stream          — вкл/выкл потоковый вывод
    /help            — показать справку
    /exit            — выход
"""

import json
import os
import sys
import re

try:
    import requests
except ImportError:
    print("Установи requests: pip install requests")
    sys.exit(1)

# ─── Конфигурация ────────────────────────────────────────────────────────────

BASE_URL = "https://api.freetheai.xyz/v1"

POPULAR_MODELS = [
    # GPT
    "bbl/gpt-5.4",
    "bbl/gpt-5.4-mini",
    "bbl/gpt-5",
    "bbl/gpt-5-mini",
    "bbl/gpt-4.1",
    # Claude
    "bbl/claude-4.6-sonnet",
    "bbl/claude-4.5-sonnet",
    "bbl/claude-4.5-opus",
    "bbl/claude-3.7-sonnet",
    # Gemini
    "bbl/gemini-3.1-pro",
    "bbl/gemini-3.0-pro",
    "bbl/gemini-2.5-pro",
    "bbl/gemini-2.5-flash",
    # GLM
    "glm/glm-5.1",
    # Grok
    "bbl/grok-4",
    "bbl/grok-3",
    # DeepSeek
    "bbl/deepseek-r1",
    "bbl/deepseek-v3",
    # Reasoning
    "bbl/o3",
    "bbl/o3-mini",
]

DEFAULT_MODEL = "bbl/gpt-5.4"
HISTORY_FILE = "freetheai_history.json"

# ─── Загрузка .env ───────────────────────────────────────────────────────────

def load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value

# ─── API ─────────────────────────────────────────────────────────────────────

class FreeTheAiChat:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = DEFAULT_MODEL
        self.history: list[dict] = []
        self.system_prompt: str | None = None
        self.stream_mode = True

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def fetch_models(self) -> list[str]:
        try:
            r = requests.get(f"{BASE_URL}/models", headers=self._headers(), timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                return sorted([m["id"] for m in data if "id" in m])
        except Exception as e:
            print(f"  Ошибка загрузки моделей: {e}")
        return []

    def _build_messages(self, user_msg: str) -> list[dict]:
        msgs = []
        if self.system_prompt:
            msgs.append({"role": "system", "content": self.system_prompt})
        msgs.extend(self.history)
        msgs.append({"role": "user", "content": user_msg})
        return msgs

    def chat(self, user_msg: str) -> str | None:
        messages = self._build_messages(user_msg)
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": self.stream_mode,
        }

        try:
            if self.stream_mode:
                return self._stream_request(payload, user_msg)
            else:
                return self._normal_request(payload, user_msg)
        except KeyboardInterrupt:
            print()
            return None
        except Exception as e:
            print(f"\n  Ошибка: {e}")
            return None

    def _normal_request(self, payload: dict, user_msg: str) -> str | None:
        r = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=120,
        )
        if r.status_code != 200:
            print(f"  Ошибка API [{r.status_code}]: {r.text[:200]}")
            return None

        data = r.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if content:
            self.history.append({"role": "user", "content": user_msg})
            self.history.append({"role": "assistant", "content": content})
            print(f"\n  {self.model}: {content}")
        return content

    def _stream_request(self, payload: dict, user_msg: str) -> str | None:
        r = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=120,
            stream=True,
        )
        if r.status_code != 200:
            print(f"  Ошибка API [{r.status_code}]: {r.text[:200]}")
            return None

        full_text = ""
        print(f"\n  {self.model}: ", end="", flush=True)

        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    print(token, end="", flush=True)
                    full_text += token
            except json.JSONDecodeError:
                continue

        print()

        if full_text:
            self.history.append({"role": "user", "content": user_msg})
            self.history.append({"role": "assistant", "content": full_text})
        return full_text

    def clear_history(self):
        self.history.clear()
        print("  История очищена.")

    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt if prompt else None
        if prompt:
            print(f"  Системный промт установлен: {prompt[:80]}...")
        else:
            print("  Системный промт сброшен.")

    def save_history(self):
        data = {
            "model": self.model,
            "system_prompt": self.system_prompt,
            "history": self.history,
        }
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError:
            pass

    def load_history(self):
        if not os.path.exists(HISTORY_FILE):
            return
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.history = data.get("history", [])
            self.system_prompt = data.get("system_prompt")
            saved_model = data.get("model")
            if saved_model:
                self.model = saved_model
        except (json.JSONDecodeError, IOError):
            pass

# ─── Интерфейс ───────────────────────────────────────────────────────────────

def print_banner():
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║        FreeTheAi Chat — бесплатный GPT       ║")
    print("  ║   api.freetheai.xyz · Discord: /signup        ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()

def print_help():
    print("""
  Команды:
    /model           — выбрать модель из списка
    /models          — показать все модели с API
    /clear           — очистить историю
    /system <текст>  — задать системный промт
    /stream          — вкл/выкл потоковый вывод
    /save            — сохранить историю в файл
    /load            — загрузить историю из файла
    /help            — эта справка
    /exit            — выход
""")

def choose_model(bot: FreeTheAiChat):
    print("\n  Популярные модели:")
    for i, m in enumerate(POPULAR_MODELS, 1):
        marker = " ◀" if m == bot.model else ""
        print(f"    {i:2}. {m}{marker}")
    print(f"\n  Текущая: {bot.model}")
    print("  Введи номер, название модели, или Enter для отмены:")

    choice = input("  > ").strip()
    if not choice:
        return

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(POPULAR_MODELS):
            bot.model = POPULAR_MODELS[idx]
            print(f"  Модель: {bot.model}")
        else:
            print("  Неверный номер.")
    else:
        bot.model = choice
        print(f"  Модель: {bot.model}")

def show_all_models(bot: FreeTheAiChat):
    print("\n  Загрузка списка моделей с API...")
    models = bot.fetch_models()
    if not models:
        print("  Не удалось загрузить. Используй /model для популярных.")
        return

    # Group by prefix
    groups: dict[str, list[str]] = {}
    for m in models:
        prefix = m.split("/")[0] if "/" in m else "other"
        groups.setdefault(prefix, []).append(m)

    for prefix in sorted(groups):
        print(f"\n  [{prefix}]")
        for m in groups[prefix]:
            marker = " ◀" if m == bot.model else ""
            print(f"    {m}{marker}")
    print(f"\n  Всего: {len(models)} моделей")
    print("  Используй /model чтобы выбрать")

def get_api_key() -> str:
    key = os.environ.get("FREETHEAI_KEY", "").strip()
    if key:
        return key

    print("  API ключ не найден в .env или переменных окружения.")
    print("  Получи ключ: Discord https://discord.gg/secrets → /signup")
    print()
    key = input("  Введи API ключ: ").strip()
    if not key:
        print("  Ключ не введён, выход.")
        sys.exit(1)
    return key

def main():
    load_dotenv()
    print_banner()

    api_key = get_api_key()
    bot = FreeTheAiChat(api_key)
    bot.load_history()

    print(f"  Модель: {bot.model}")
    print(f"  Стрим: {'вкл' if bot.stream_mode else 'выкл'}")
    if bot.system_prompt:
        print(f"  Системный промт: {bot.system_prompt[:60]}...")
    if bot.history:
        print(f"  Загружена история: {len(bot.history)} сообщений")
    print("  Введи /help для справки\n")

    try:
        while True:
            try:
                user_input = input("  Ты: ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            cmd = user_input.lower()

            if cmd in ("/exit", "/quit", "/выход"):
                break
            elif cmd in ("/help", "/помощь"):
                print_help()
            elif cmd in ("/model", "/модель"):
                choose_model(bot)
            elif cmd in ("/models", "/модели"):
                show_all_models(bot)
            elif cmd in ("/clear", "/сброс"):
                bot.clear_history()
            elif cmd in ("/stream", "/стрим"):
                bot.stream_mode = not bot.stream_mode
                print(f"  Стрим: {'вкл' if bot.stream_mode else 'выкл'}")
            elif cmd in ("/save", "/сохранить"):
                bot.save_history()
                print(f"  История сохранена в {HISTORY_FILE}")
            elif cmd in ("/load", "/загрузить"):
                bot.load_history()
                print(f"  История загружена ({len(bot.history)} сообщений)")
            elif user_input.startswith("/system "):
                bot.set_system_prompt(user_input[8:].strip())
            elif user_input.startswith("/система "):
                bot.set_system_prompt(user_input[9:].strip())
            elif user_input.startswith("/"):
                print("  Неизвестная команда. /help для справки.")
            else:
                bot.chat(user_input)

    except KeyboardInterrupt:
        print("\n")

    bot.save_history()
    print("  До встречи!")

if __name__ == "__main__":
    main()
