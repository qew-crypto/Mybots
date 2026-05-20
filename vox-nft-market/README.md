# Vox NFT Market

Telegram-бот для автоматического выкупа NFT-подарков. Премиальный Web3-сервис с тёмным неоновым стилем.

## Возможности

- **Продажа NFT** — отправьте ссылку `t.me/nft/Name-12345`, бот оценит подарок по данным GetGems
- **Автопроверка передачи** — бот отслеживает смену владельца NFT
- **Профиль** — баланс, история продаж, статистика
- **Вывод средств** — СБП, карта, USDT, TON, зарубежная карта
- **Отзывы** — система отзывов после успешных сделок
- **Админ-панель** — полное управление ботом

## Быстрый старт

### 1. Клонируйте репозиторий

```bash
git clone https://github.com/qew-crypto/vox-nft-market.git
cd vox-nft-market
```

### 2. Установите зависимости

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

### 3. Настройте переменные окружения

```bash
cp .env.example .env
# Отредактируйте .env — укажите BOT_TOKEN и ADMIN_IDS
```

### 4. Запустите бота

```bash
python main.py
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/sell` | Продать NFT |
| `/profile` | Профиль |
| `/reviews` | Отзывы |
| `/support` | Поддержка |
| `/admin` | Админ-панель (только для админов) |

## Админ-панель

Доступна по команде `/admin` для пользователей из `ADMIN_IDS`.

Функции:
- Статистика бота
- Управление пользователями
- Обработка заявок на вывод
- Просмотр сделок
- Рассылка
- Бан/разбан
- Начисление/списание баланса
- Настройка курса, процента оценки, получателя NFT
- Просмотр логов

## Структура проекта

```
vox-nft-market/
├── bot/
│   ├── config.py          # Конфигурация
│   ├── database.py        # БД (SQLite)
│   ├── keyboards.py       # Inline-клавиатуры
│   ├── handlers/
│   │   ├── start.py       # /start, главное меню
│   │   ├── sell.py        # Продажа NFT
│   │   ├── profile.py     # Профиль, вывод
│   │   ├── reviews.py     # Отзывы
│   │   ├── support.py     # Поддержка
│   │   └── admin.py       # Админ-панель
│   └── services/
│       ├── nft.py         # Парсинг NFT, GetGems API
│       └── currency.py    # Конвертация TON → RUB
├── main.py                # Точка входа
├── requirements.txt
├── .env.example
└── README.md
```

## Технологии

- **Python 3.11+**
- **aiogram 3.x** — Telegram Bot API
- **aiosqlite** — асинхронный SQLite
- **aiohttp** — HTTP-запросы к API
- **GetGems API** — цены NFT
- **CoinGecko / Binance** — курс TON/RUB
