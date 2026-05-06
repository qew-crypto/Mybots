from __future__ import annotations

import random
import string
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

import aiosqlite

from models import DEFAULT_PAYMENT_METHOD, DEFAULT_SETTINGS, FORCED_TEXT_SETTING_KEYS, UI_TEXT_VERSION

MONEY_Q = Decimal("0.01")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def money_str(value: object) -> str:
    return str(Decimal(str(value)).quantize(MONEY_Q, rounding=ROUND_HALF_UP))


def norm_code(value: str) -> str:
    return "".join(value.strip().upper().split())


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.conn.execute("PRAGMA journal_mode = WAL")
        await self.conn.commit()

    def _db(self) -> aiosqlite.Connection:
        if self.conn is None:
            raise RuntimeError("Database is not connected")
        return self.conn

    async def close(self) -> None:
        if self.conn is not None:
            await self.conn.close()

    async def init(self) -> None:
        db = self._db()
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                first_name TEXT,
                registered_at TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                is_banned INTEGER NOT NULL DEFAULT 0,
                note TEXT NOT NULL DEFAULT '',
                balance TEXT NOT NULL DEFAULT '0',
                referrer_user_id INTEGER,
                ref_bonus_total TEXT NOT NULL DEFAULT '0'
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_type TEXT NOT NULL CHECK(order_type IN ('buy', 'sell')),
                gold_amount TEXT NOT NULL,
                rate TEXT NOT NULL,
                total_amount TEXT NOT NULL,
                payment_details TEXT,
                user_payment_details TEXT,
                receipt_file_id TEXT,
                receipt_file_type TEXT,
                comment TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                balance_used TEXT NOT NULL DEFAULT '0',
                payment_due TEXT NOT NULL DEFAULT '0',
                balance_refunded INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS payment_methods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                bank_name TEXT,
                card_number TEXT,
                phone_number TEXT,
                recipient_name TEXT,
                comment TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                admin_answer TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS mailings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                photo_file_id TEXT,
                created_at TEXT NOT NULL,
                sent_count INTEGER NOT NULL DEFAULT 0,
                failed_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                order_id INTEGER,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                text TEXT NOT NULL,
                is_anonymous INTEGER NOT NULL DEFAULT 1,
                display_name TEXT NOT NULL DEFAULT 'Аноним',
                created_at TEXT NOT NULL,
                is_seed INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(order_id) REFERENCES orders(id)
            );

            CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                amount TEXT NOT NULL,
                max_activations INTEGER NOT NULL,
                activations_count INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                is_unique INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS promo_activations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                promo_id INTEGER NOT NULL,
                amount TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, promo_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(promo_id) REFERENCES promo_codes(id)
            );

            CREATE TABLE IF NOT EXISTS balance_topups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount TEXT NOT NULL,
                payment_details TEXT,
                receipt_file_id TEXT,
                receipt_file_type TEXT,
                comment TEXT,
                status TEXT NOT NULL DEFAULT 'waiting_payment',
                ref_bonus_paid TEXT NOT NULL DEFAULT '0',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
            CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_user_id);
            CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
            CREATE INDEX IF NOT EXISTS idx_support_status ON support_tickets(status);
            CREATE INDEX IF NOT EXISTS idx_reviews_order ON reviews(order_id);
            CREATE INDEX IF NOT EXISTS idx_promo_code ON promo_codes(code);
            CREATE INDEX IF NOT EXISTS idx_topups_status ON balance_topups(status);
            """
        )
        await db.commit()
        await self.migrate()
        await self.ensure_default_settings()
        await self.ensure_default_payment_method()
        await self.seed_default_reviews()

    async def migrate(self) -> None:
        await self._add_column_if_missing("users", "balance", "TEXT NOT NULL DEFAULT '0'")
        await self._add_column_if_missing("users", "referrer_user_id", "INTEGER")
        await self._add_column_if_missing("users", "ref_bonus_total", "TEXT NOT NULL DEFAULT '0'")
        await self._add_column_if_missing("orders", "balance_used", "TEXT NOT NULL DEFAULT '0'")
        await self._add_column_if_missing("orders", "payment_due", "TEXT NOT NULL DEFAULT '0'")
        await self._add_column_if_missing("orders", "balance_refunded", "INTEGER NOT NULL DEFAULT 0")
        await self._db().commit()

    async def _column_exists(self, table: str, column: str) -> bool:
        async with self._db().execute(f"PRAGMA table_info({table})") as cursor:
            rows = await cursor.fetchall()
        return any(row["name"] == column for row in rows)

    async def _add_column_if_missing(self, table: str, column: str, ddl: str) -> None:
        if not await self._column_exists(table, column):
            await self._db().execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    async def ensure_default_settings(self) -> None:
        db = self._db()
        version_row = await self.fetchone("SELECT value FROM settings WHERE key = ?", ("ui_text_version",))
        current_version = version_row["value"] if version_row else ""

        for key, value in DEFAULT_SETTINGS.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
                (key, value),
            )

        if current_version != UI_TEXT_VERSION:
            for key in FORCED_TEXT_SETTING_KEYS:
                await db.execute(
                    "UPDATE settings SET value = ? WHERE key = ?",
                    (DEFAULT_SETTINGS[key], key),
                )
            await db.execute(
                "INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)",
                ("ui_text_version", UI_TEXT_VERSION),
            )

        await db.commit()

    async def ensure_default_payment_method(self) -> None:
        db = self._db()
        url = DEFAULT_PAYMENT_METHOD["card_number"]
        row = await self.fetchone(
            """
            SELECT * FROM payment_methods
            WHERE card_number = ? OR lower(title) LIKE '%donate%'
            ORDER BY id DESC
            LIMIT 1
            """,
            (url,),
        )
        values = (
            DEFAULT_PAYMENT_METHOD["title"],
            DEFAULT_PAYMENT_METHOD["bank_name"],
            DEFAULT_PAYMENT_METHOD["card_number"],
            DEFAULT_PAYMENT_METHOD["phone_number"],
            DEFAULT_PAYMENT_METHOD["recipient_name"],
            DEFAULT_PAYMENT_METHOD["comment"],
        )
        if row:
            await db.execute(
                """
                UPDATE payment_methods
                SET title = ?, bank_name = ?, card_number = ?, phone_number = ?,
                    recipient_name = ?, comment = ?, is_active = 1
                WHERE id = ?
                """,
                (*values, row["id"]),
            )
        else:
            await db.execute(
                """
                INSERT INTO payment_methods(
                    title, bank_name, card_number, phone_number, recipient_name, comment, is_active
                )
                VALUES(?, ?, ?, ?, ?, ?, 1)
                """,
                values,
            )
        await db.commit()

    async def seed_default_reviews(self) -> None:
        seed_count_row = await self.fetchone("SELECT COUNT(*) AS c FROM reviews WHERE is_seed = 1")
        seed_count = int(seed_count_row["c"] or 0)
        if seed_count >= 500:
            return

        names = ["Аноним", "@player_so2", "@goldbuyer", "@standoff_user", "@vox_client", "Аноним"]
        samples = [
            "Быстро выдали голду, всё ровно.",
            "Оплатил, написал в поддержку, через пару минут получил.",
            "Покупаю не первый раз, магазин норм.",
            "Админ ответил быстро, сделка прошла спокойно.",
            "Удобно, что можно оплатить картой через DonateAlerts.",
            "Продал голду, выплату получил без проблем.",
            "Всё честно, рекомендую.",
            "Хороший курс и понятный бот.",
            "Проверка ручная, зато безопасно.",
            "Спасибо, всё пришло.",
        ]
        last_five = [
            (5, "Голда пришла быстро, поддержка помогла сразу.", "@kaw_client"),
            (5, "Пополнял баланс и купил через него, удобно.", "Аноним"),
            (5, "Продал голду, выплатили после проверки.", "@so2seller"),
            (4, "Немного подождал ответ, но сделка завершена нормально.", "Аноним"),
            (5, "VoxShop топ, буду брать ещё.", "@vox_gold"),
        ]
        rnd = random.Random(228)
        db = self._db()
        start = datetime.now(timezone.utc) - timedelta(days=90)
        to_add = 632 - seed_count
        if to_add < 0:
            to_add = 0
        for idx in range(to_add):
            rating = rnd.choices([5, 4, 3], weights=[82, 16, 2], k=1)[0]
            text = rnd.choice(samples)
            name = rnd.choice(names)
            is_anon = 1 if name == "Аноним" else 0
            created = (start + timedelta(hours=idx * 3)).isoformat(timespec="seconds")
            await db.execute(
                """
                INSERT INTO reviews(user_id, order_id, rating, text, is_anonymous, display_name, created_at, is_seed)
                VALUES(NULL, NULL, ?, ?, ?, ?, ?, 1)
                """,
                (rating, text, is_anon, name, created),
            )
        for idx, (rating, text, name) in enumerate(last_five):
            created = (datetime.now(timezone.utc) + timedelta(seconds=idx)).isoformat(timespec="seconds")
            await db.execute(
                """
                INSERT INTO reviews(user_id, order_id, rating, text, is_anonymous, display_name, created_at, is_seed)
                VALUES(NULL, NULL, ?, ?, ?, ?, ?, 1)
                """,
                (rating, text, 1 if name == "Аноним" else 0, name, created),
            )
        await db.execute("INSERT OR REPLACE INTO settings(key, value) VALUES('seed_reviews_done', '1')")
        await db.commit()

    async def ensure_admin_ids(self, admin_ids: Iterable[int]) -> None:
        db = self._db()
        for telegram_id in admin_ids:
            await db.execute(
                """
                INSERT INTO users(telegram_id, username, first_name, registered_at, is_admin)
                VALUES(?, NULL, 'Admin', ?, 1)
                ON CONFLICT(telegram_id) DO UPDATE SET is_admin = 1
                """,
                (telegram_id, now_iso()),
            )
        await db.commit()

    async def fetchone(self, query: str, params: tuple = ()):  # noqa: ANN201
        async with self._db().execute(query, params) as cursor:
            return await cursor.fetchone()

    async def fetchall(self, query: str, params: tuple = ()):  # noqa: ANN201
        async with self._db().execute(query, params) as cursor:
            return await cursor.fetchall()

    async def execute(self, query: str, params: tuple = ()) -> int:
        cursor = await self._db().execute(query, params)
        await self._db().commit()
        return int(cursor.lastrowid or 0)

    async def upsert_user(self, tg_user) -> aiosqlite.Row:  # noqa: ANN001
        db = self._db()
        await db.execute(
            """
            INSERT INTO users(telegram_id, username, first_name, registered_at)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (
                tg_user.id,
                getattr(tg_user, "username", None),
                getattr(tg_user, "first_name", None),
                now_iso(),
            ),
        )
        await db.commit()
        row = await self.get_user_by_tg(tg_user.id)
        if row is None:
            raise RuntimeError("Failed to create user")
        return row

    async def get_user_by_tg(self, telegram_id: int):
        return await self.fetchone(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )

    async def get_user_by_id(self, user_id: int):
        return await self.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))

    async def get_admin_telegram_ids(self) -> list[int]:
        rows = await self.fetchall(
            "SELECT telegram_id FROM users WHERE is_admin = 1 AND is_banned = 0"
        )
        return [int(row["telegram_id"]) for row in rows]

    async def is_admin(self, telegram_id: int) -> bool:
        row = await self.get_user_by_tg(telegram_id)
        return bool(row and row["is_admin"])

    async def set_referrer_if_possible(self, user_id: int, referrer_telegram_id: int) -> bool:
        user = await self.get_user_by_id(user_id)
        referrer = await self.get_user_by_tg(referrer_telegram_id)
        if not user or not referrer:
            return False
        if int(user["telegram_id"]) == int(referrer_telegram_id):
            return False
        if user["referrer_user_id"]:
            return False
        await self.execute(
            "UPDATE users SET referrer_user_id = ? WHERE id = ? AND referrer_user_id IS NULL",
            (referrer["id"], user_id),
        )
        return True

    async def get_referral_count(self, user_id: int) -> int:
        row = await self.fetchone("SELECT COUNT(*) AS c FROM users WHERE referrer_user_id = ?", (user_id,))
        return int(row["c"] or 0)

    async def set_user_banned(self, user_id: int, banned: bool) -> None:
        await self.execute(
            "UPDATE users SET is_banned = ? WHERE id = ?",
            (1 if banned else 0, user_id),
        )

    async def set_user_admin(self, telegram_id: int, is_admin: bool) -> None:
        row = await self.get_user_by_tg(telegram_id)
        if row:
            await self.execute(
                "UPDATE users SET is_admin = ? WHERE telegram_id = ?",
                (1 if is_admin else 0, telegram_id),
            )
        else:
            await self.execute(
                """
                INSERT INTO users(telegram_id, username, first_name, registered_at, is_admin)
                VALUES(?, NULL, 'Admin', ?, ?)
                """,
                (telegram_id, now_iso(), 1 if is_admin else 0),
            )

    async def set_user_note(self, user_id: int, note: str) -> None:
        await self.execute("UPDATE users SET note = ? WHERE id = ?", (note, user_id))

    async def set_user_balance(self, user_id: int, balance: str) -> None:
        await self.execute("UPDATE users SET balance = ? WHERE id = ?", (money_str(balance), user_id))

    async def add_user_balance(self, user_id: int, amount: str | Decimal) -> None:
        user = await self.get_user_by_id(user_id)
        if not user:
            return
        new_balance = Decimal(str(user["balance"] or "0")) + Decimal(str(amount))
        await self.execute("UPDATE users SET balance = ? WHERE id = ?", (money_str(new_balance), user_id))

    async def search_users(self, query: str, limit: int = 20):
        raw = query.strip().lstrip("@")
        if raw.isdigit():
            return await self.fetchall(
                """
                SELECT * FROM users
                WHERE telegram_id = ? OR id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(raw), int(raw), limit),
            )
        like = f"%{raw}%"
        return await self.fetchall(
            """
            SELECT * FROM users
            WHERE username LIKE ? OR first_name LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (like, like, limit),
        )

    async def create_order(
        self,
        *,
        user_id: int,
        order_type: str,
        gold_amount: str,
        rate: str,
        total_amount: str,
        payment_details: str | None,
        user_payment_details: str | None,
        receipt_file_id: str | None,
        receipt_file_type: str | None,
        comment: str | None,
        status: str,
        balance_used: str = "0",
        payment_due: str | None = None,
    ) -> int:
        created = now_iso()
        payment_due_value = payment_due if payment_due is not None else total_amount
        return await self.execute(
            """
            INSERT INTO orders(
                user_id, order_type, gold_amount, rate, total_amount,
                payment_details, user_payment_details, receipt_file_id,
                receipt_file_type, comment, status, created_at, updated_at,
                balance_used, payment_due
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                order_type,
                gold_amount,
                rate,
                total_amount,
                payment_details,
                user_payment_details,
                receipt_file_id,
                receipt_file_type,
                comment,
                status,
                created,
                created,
                money_str(balance_used),
                money_str(payment_due_value),
            ),
        )

    async def create_order_with_balance_deduction(
        self,
        *,
        user_id: int,
        order_type: str,
        gold_amount: str,
        rate: str,
        total_amount: str,
        payment_details: str | None,
        user_payment_details: str | None,
        receipt_file_id: str | None,
        receipt_file_type: str | None,
        comment: str | None,
        status: str,
        balance_used: str,
        payment_due: str,
    ) -> int:
        balance_dec = Decimal(str(balance_used or "0"))
        if balance_dec <= 0:
            return await self.create_order(
                user_id=user_id,
                order_type=order_type,
                gold_amount=gold_amount,
                rate=rate,
                total_amount=total_amount,
                payment_details=payment_details,
                user_payment_details=user_payment_details,
                receipt_file_id=receipt_file_id,
                receipt_file_type=receipt_file_type,
                comment=comment,
                status=status,
                balance_used="0",
                payment_due=payment_due,
            )

        db = self._db()
        try:
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()
            if user is None:
                raise RuntimeError("User not found")
            current = Decimal(str(user["balance"] or "0"))
            if current < balance_dec:
                raise ValueError("Недостаточно средств на балансе")
            new_balance = current - balance_dec
            await db.execute("UPDATE users SET balance = ? WHERE id = ?", (money_str(new_balance), user_id))
            created = now_iso()
            cursor = await db.execute(
                """
                INSERT INTO orders(
                    user_id, order_type, gold_amount, rate, total_amount,
                    payment_details, user_payment_details, receipt_file_id,
                    receipt_file_type, comment, status, created_at, updated_at,
                    balance_used, payment_due
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    order_type,
                    gold_amount,
                    rate,
                    total_amount,
                    payment_details,
                    user_payment_details,
                    receipt_file_id,
                    receipt_file_type,
                    comment,
                    status,
                    created,
                    created,
                    money_str(balance_dec),
                    money_str(payment_due),
                ),
            )
            await db.commit()
            return int(cursor.lastrowid or 0)
        except Exception:
            await db.rollback()
            raise

    async def get_order(self, order_id: int):
        return await self.fetchone("SELECT * FROM orders WHERE id = ?", (order_id,))

    async def get_order_with_user(self, order_id: int):
        return await self.fetchone(
            """
            SELECT
                orders.*,
                users.telegram_id,
                users.username,
                users.first_name,
                users.is_banned,
                users.balance
            FROM orders
            JOIN users ON users.id = orders.user_id
            WHERE orders.id = ?
            """,
            (order_id,),
        )

    async def list_orders(self, category: str = "new", limit: int = 10):
        if category == "all":
            return await self.fetchall(
                "SELECT * FROM orders ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        if category == "active":
            return await self.fetchall(
                """
                SELECT * FROM orders
                WHERE status IN ('new', 'waiting_payment', 'paid', 'in_progress')
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
        if category == "completed":
            return await self.fetchall(
                "SELECT * FROM orders WHERE status = 'completed' ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        if category == "rejected":
            return await self.fetchall(
                """
                SELECT * FROM orders
                WHERE status IN ('rejected', 'cancelled')
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
        return await self.fetchall(
            "SELECT * FROM orders WHERE status = ? ORDER BY id DESC LIMIT ?",
            (category, limit),
        )

    async def list_user_orders(self, user_id: int, category: str = "active", limit: int = 10):
        if category == "active":
            return await self.fetchall(
                """
                SELECT * FROM orders
                WHERE user_id = ? AND status IN ('new', 'waiting_payment', 'paid', 'in_progress')
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
        if category == "completed":
            return await self.fetchall(
                """
                SELECT * FROM orders
                WHERE user_id = ? AND status = 'completed'
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
        if category == "rejected":
            return await self.fetchall(
                """
                SELECT * FROM orders
                WHERE user_id = ? AND status IN ('rejected', 'cancelled')
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
        return await self.fetchall(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )

    async def update_order_status(self, order_id: int, status: str) -> None:
        db = self._db()
        order = await self.get_order(order_id)
        if order is None:
            return
        await db.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
            (status, now_iso(), order_id),
        )
        balance_used = Decimal(str(order["balance_used"] or "0"))
        should_refund = (
            status in {"rejected", "cancelled"}
            and balance_used > 0
            and not bool(order["balance_refunded"])
        )
        if should_refund:
            user = await self.get_user_by_id(order["user_id"])
            if user:
                new_balance = Decimal(str(user["balance"] or "0")) + balance_used
                await db.execute("UPDATE users SET balance = ? WHERE id = ?", (money_str(new_balance), order["user_id"]))
                await db.execute("UPDATE orders SET balance_refunded = 1 WHERE id = ?", (order_id,))
        await db.commit()

    async def get_user_order_stats(self, user_id: int) -> dict:
        row = await self.fetchone(
            """
            SELECT
                SUM(CASE WHEN order_type = 'buy' AND status = 'completed' THEN 1 ELSE 0 END) AS buy_count,
                SUM(CASE WHEN order_type = 'sell' AND status = 'completed' THEN 1 ELSE 0 END) AS sell_count,
                SUM(CASE WHEN status = 'completed' THEN CAST(total_amount AS REAL) ELSE 0 END) AS total_sum
            FROM orders
            WHERE user_id = ?
            """,
            (user_id,),
        )
        topup = await self.fetchone(
            "SELECT SUM(CASE WHEN status = 'completed' THEN CAST(amount AS REAL) ELSE 0 END) AS s FROM balance_topups WHERE user_id = ?",
            (user_id,),
        )
        reviews = await self.fetchone("SELECT COUNT(*) AS c FROM reviews WHERE user_id = ?", (user_id,))
        refs = await self.fetchone("SELECT COUNT(*) AS c FROM users WHERE referrer_user_id = ?", (user_id,))
        return {
            "buy_count": int(row["buy_count"] or 0),
            "sell_count": int(row["sell_count"] or 0),
            "total_sum": row["total_sum"] or 0,
            "topup_sum": topup["s"] or 0,
            "review_count": int(reviews["c"] or 0),
            "ref_count": int(refs["c"] or 0),
        }

    async def get_settings(self) -> dict[str, str]:
        rows = await self.fetchall("SELECT key, value FROM settings")
        data = {row["key"]: row["value"] for row in rows}
        for key, value in DEFAULT_SETTINGS.items():
            data.setdefault(key, value)
        return data

    async def get_setting(self, key: str) -> str:
        row = await self.fetchone("SELECT value FROM settings WHERE key = ?", (key,))
        if row:
            return str(row["value"])
        return DEFAULT_SETTINGS.get(key, "")

    async def set_setting(self, key: str, value: str) -> None:
        await self.execute(
            """
            INSERT INTO settings(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

    async def list_payment_methods(self, active_only: bool = False):
        default_url = DEFAULT_PAYMENT_METHOD["card_number"]
        if active_only:
            return await self.fetchall(
                """
                SELECT * FROM payment_methods
                WHERE is_active = 1
                ORDER BY CASE WHEN card_number = ? THEN 0 ELSE 1 END, id DESC
                """,
                (default_url,),
            )
        return await self.fetchall(
            """
            SELECT * FROM payment_methods
            ORDER BY CASE WHEN card_number = ? THEN 0 ELSE 1 END, id DESC
            """,
            (default_url,),
        )

    async def get_payment_method(self, method_id: int):
        return await self.fetchone("SELECT * FROM payment_methods WHERE id = ?", (method_id,))

    async def add_payment_method(
        self,
        *,
        title: str,
        bank_name: str | None,
        card_number: str | None,
        phone_number: str | None,
        recipient_name: str | None,
        comment: str | None,
    ) -> int:
        return await self.execute(
            """
            INSERT INTO payment_methods(
                title, bank_name, card_number, phone_number, recipient_name, comment, is_active
            )
            VALUES(?, ?, ?, ?, ?, ?, 1)
            """,
            (title, bank_name, card_number, phone_number, recipient_name, comment),
        )

    async def update_payment_method_field(self, method_id: int, field: str, value: str | None) -> None:
        if field not in {"title", "bank_name", "card_number", "phone_number", "recipient_name", "comment"}:
            raise ValueError("Invalid payment field")
        await self.execute(
            f"UPDATE payment_methods SET {field} = ? WHERE id = ?",
            (value, method_id),
        )

    async def toggle_payment_method(self, method_id: int) -> None:
        await self.execute(
            """
            UPDATE payment_methods
            SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END
            WHERE id = ?
            """,
            (method_id,),
        )

    async def delete_payment_method(self, method_id: int) -> None:
        await self.execute("DELETE FROM payment_methods WHERE id = ?", (method_id,))

    # Balance top-ups
    async def create_topup(
        self,
        *,
        user_id: int,
        amount: str,
        payment_details: str | None,
        receipt_file_id: str | None,
        receipt_file_type: str | None,
        comment: str | None,
    ) -> int:
        created = now_iso()
        return await self.execute(
            """
            INSERT INTO balance_topups(
                user_id, amount, payment_details, receipt_file_id, receipt_file_type,
                comment, status, created_at, updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, 'waiting_payment', ?, ?)
            """,
            (user_id, money_str(amount), payment_details, receipt_file_id, receipt_file_type, comment, created, created),
        )

    async def get_topup_with_user(self, topup_id: int):
        return await self.fetchone(
            """
            SELECT balance_topups.*, users.telegram_id, users.username, users.first_name,
                   users.balance, users.referrer_user_id
            FROM balance_topups
            JOIN users ON users.id = balance_topups.user_id
            WHERE balance_topups.id = ?
            """,
            (topup_id,),
        )

    async def list_topups(self, status: str = "waiting_payment", limit: int = 12):
        if status == "all":
            return await self.fetchall(
                """
                SELECT balance_topups.*, users.telegram_id, users.username, users.first_name
                FROM balance_topups
                JOIN users ON users.id = balance_topups.user_id
                ORDER BY balance_topups.id DESC
                LIMIT ?
                """,
                (limit,),
            )
        return await self.fetchall(
            """
            SELECT balance_topups.*, users.telegram_id, users.username, users.first_name
            FROM balance_topups
            JOIN users ON users.id = balance_topups.user_id
            WHERE balance_topups.status = ?
            ORDER BY balance_topups.id DESC
            LIMIT ?
            """,
            (status, limit),
        )

    async def reject_topup(self, topup_id: int) -> None:
        await self.execute(
            "UPDATE balance_topups SET status = 'rejected', updated_at = ? WHERE id = ? AND status = 'waiting_payment'",
            (now_iso(), topup_id),
        )

    async def confirm_topup(self, topup_id: int) -> dict:
        db = self._db()
        try:
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                """
                SELECT balance_topups.*, users.telegram_id, users.balance, users.referrer_user_id
                FROM balance_topups
                JOIN users ON users.id = balance_topups.user_id
                WHERE balance_topups.id = ?
                """,
                (topup_id,),
            ) as cursor:
                topup = await cursor.fetchone()
            if topup is None:
                await db.rollback()
                return {"ok": False, "reason": "not_found"}
            if topup["status"] == "completed":
                await db.rollback()
                return {"ok": False, "reason": "already_completed"}
            if topup["status"] != "waiting_payment":
                await db.rollback()
                return {"ok": False, "reason": "bad_status"}

            amount = Decimal(str(topup["amount"]))
            new_balance = Decimal(str(topup["balance"] or "0")) + amount
            await db.execute("UPDATE users SET balance = ? WHERE id = ?", (money_str(new_balance), topup["user_id"]))

            bonus = Decimal("0")
            referrer_tg = None
            referrer_id = topup["referrer_user_id"]
            if referrer_id:
                async with db.execute("SELECT * FROM users WHERE id = ?", (referrer_id,)) as ref_cur:
                    ref_user = await ref_cur.fetchone()
                if ref_user:
                    bonus = (amount * Decimal("0.10")).quantize(MONEY_Q, rounding=ROUND_HALF_UP)
                    ref_new_balance = Decimal(str(ref_user["balance"] or "0")) + bonus
                    ref_bonus_total = Decimal(str(ref_user["ref_bonus_total"] or "0")) + bonus
                    await db.execute(
                        "UPDATE users SET balance = ?, ref_bonus_total = ? WHERE id = ?",
                        (money_str(ref_new_balance), money_str(ref_bonus_total), ref_user["id"]),
                    )
                    referrer_tg = ref_user["telegram_id"]

            await db.execute(
                """
                UPDATE balance_topups
                SET status = 'completed', updated_at = ?, ref_bonus_paid = ?
                WHERE id = ?
                """,
                (now_iso(), money_str(bonus), topup_id),
            )
            await db.commit()
            return {
                "ok": True,
                "telegram_id": topup["telegram_id"],
                "amount": money_str(amount),
                "new_balance": money_str(new_balance),
                "bonus": money_str(bonus),
                "referrer_tg": referrer_tg,
            }
        except Exception:
            await db.rollback()
            raise

    # Promo codes
    async def create_promo(self, *, code: str, amount: str, max_activations: int, is_unique: bool) -> int:
        return await self.execute(
            """
            INSERT INTO promo_codes(code, amount, max_activations, activations_count, is_active, is_unique, created_at)
            VALUES(?, ?, ?, 0, 1, ?, ?)
            """,
            (norm_code(code), money_str(amount), int(max_activations), 1 if is_unique else 0, now_iso()),
        )

    async def generate_unique_promo_code(self, length: int = 10) -> str:
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(100):
            code = "VOX-" + "".join(random.choice(alphabet) for _ in range(length))
            row = await self.fetchone("SELECT id FROM promo_codes WHERE code = ?", (code,))
            if not row:
                return code
        raise RuntimeError("Could not generate promo code")

    async def list_promos(self, limit: int = 20):
        return await self.fetchall("SELECT * FROM promo_codes ORDER BY id DESC LIMIT ?", (limit,))

    async def get_promo(self, promo_id: int):
        return await self.fetchone("SELECT * FROM promo_codes WHERE id = ?", (promo_id,))

    async def toggle_promo(self, promo_id: int) -> None:
        await self.execute(
            """
            UPDATE promo_codes
            SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END
            WHERE id = ?
            """,
            (promo_id,),
        )

    async def activate_promo(self, user_id: int, code: str) -> dict:
        code_norm = norm_code(code)
        if not code_norm:
            return {"ok": False, "reason": "empty"}
        db = self._db()
        try:
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute("SELECT * FROM promo_codes WHERE code = ?", (code_norm,)) as cursor:
                promo = await cursor.fetchone()
            if promo is None:
                await db.rollback()
                return {"ok": False, "reason": "not_found"}
            if not promo["is_active"]:
                await db.rollback()
                return {"ok": False, "reason": "inactive"}
            if int(promo["activations_count"] or 0) >= int(promo["max_activations"]):
                await db.rollback()
                return {"ok": False, "reason": "limit"}
            async with db.execute(
                "SELECT id FROM promo_activations WHERE user_id = ? AND promo_id = ?",
                (user_id, promo["id"]),
            ) as check_cur:
                already = await check_cur.fetchone()
            if already:
                await db.rollback()
                return {"ok": False, "reason": "already"}
            async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as user_cur:
                user = await user_cur.fetchone()
            if user is None:
                await db.rollback()
                return {"ok": False, "reason": "user_not_found"}
            amount = Decimal(str(promo["amount"]))
            new_balance = Decimal(str(user["balance"] or "0")) + amount
            await db.execute("UPDATE users SET balance = ? WHERE id = ?", (money_str(new_balance), user_id))
            await db.execute(
                "INSERT INTO promo_activations(user_id, promo_id, amount, created_at) VALUES(?, ?, ?, ?)",
                (user_id, promo["id"], money_str(amount), now_iso()),
            )
            await db.execute(
                "UPDATE promo_codes SET activations_count = activations_count + 1 WHERE id = ?",
                (promo["id"],),
            )
            await db.commit()
            return {"ok": True, "code": promo["code"], "amount": money_str(amount), "new_balance": money_str(new_balance)}
        except Exception:
            await db.rollback()
            raise

    # Reviews
    async def create_review(
        self,
        *,
        user_id: int,
        order_id: int | None,
        rating: int,
        text: str,
        is_anonymous: bool,
        display_name: str,
    ) -> int:
        return await self.execute(
            """
            INSERT INTO reviews(user_id, order_id, rating, text, is_anonymous, display_name, created_at, is_seed)
            VALUES(?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (user_id, order_id, int(rating), text, 1 if is_anonymous else 0, display_name, now_iso()),
        )

    async def get_reviewable_orders(self, user_id: int, limit: int = 10):
        return await self.fetchall(
            """
            SELECT orders.* FROM orders
            LEFT JOIN reviews ON reviews.user_id = orders.user_id AND reviews.order_id = orders.id
            WHERE orders.user_id = ? AND orders.status = 'completed' AND reviews.id IS NULL
            ORDER BY orders.id DESC
            LIMIT ?
            """,
            (user_id, limit),
        )

    async def has_review_for_order(self, user_id: int, order_id: int) -> bool:
        row = await self.fetchone(
            "SELECT id FROM reviews WHERE user_id = ? AND order_id = ? LIMIT 1",
            (user_id, order_id),
        )
        return bool(row)

    async def get_reviews_count(self) -> int:
        row = await self.fetchone("SELECT COUNT(*) AS c FROM reviews")
        return int(row["c"] or 0)

    async def get_average_rating(self) -> float:
        row = await self.fetchone("SELECT AVG(CAST(rating AS REAL)) AS avg_rating FROM reviews")
        if row and row["avg_rating"] is not None:
            return round(float(row["avg_rating"]), 1)
        return 4.8

    async def list_recent_reviews(self, limit: int = 5):
        return await self.fetchall("SELECT * FROM reviews ORDER BY id DESC LIMIT ?", (limit,))

    async def create_manual_review(self, *, rating: int, text: str, display_name: str, is_anonymous: bool = False) -> int:
        return await self.execute(
            """
            INSERT INTO reviews(user_id, order_id, rating, text, is_anonymous, display_name, created_at, is_seed)
            VALUES(NULL, NULL, ?, ?, ?, ?, ?, 0)
            """,
            (int(rating), text, 1 if is_anonymous else 0, display_name, now_iso()),
        )

    async def list_reviews_admin(self, limit: int = 20):
        return await self.fetchall("SELECT * FROM reviews ORDER BY id DESC LIMIT ?", (limit,))

    async def get_review(self, review_id: int):
        return await self.fetchone("SELECT * FROM reviews WHERE id = ?", (review_id,))

    async def delete_review(self, review_id: int) -> None:
        await self.execute("DELETE FROM reviews WHERE id = ?", (review_id,))

    # Support and mailing
    async def create_support_ticket(self, user_id: int, message: str) -> int:
        return await self.execute(
            """
            INSERT INTO support_tickets(user_id, message, status, created_at)
            VALUES(?, ?, 'open', ?)
            """,
            (user_id, message, now_iso()),
        )

    async def get_support_ticket(self, ticket_id: int):
        return await self.fetchone(
            """
            SELECT support_tickets.*, users.telegram_id, users.username, users.first_name
            FROM support_tickets
            JOIN users ON users.id = support_tickets.user_id
            WHERE support_tickets.id = ?
            """,
            (ticket_id,),
        )

    async def list_support_tickets(self, status: str = "open", limit: int = 12):
        if status == "all":
            return await self.fetchall(
                """
                SELECT support_tickets.*, users.telegram_id, users.username, users.first_name
                FROM support_tickets
                JOIN users ON users.id = support_tickets.user_id
                ORDER BY support_tickets.id DESC
                LIMIT ?
                """,
                (limit,),
            )
        return await self.fetchall(
            """
            SELECT support_tickets.*, users.telegram_id, users.username, users.first_name
            FROM support_tickets
            JOIN users ON users.id = support_tickets.user_id
            WHERE support_tickets.status = ?
            ORDER BY support_tickets.id DESC
            LIMIT ?
            """,
            (status, limit),
        )

    async def answer_support_ticket(self, ticket_id: int, answer: str) -> None:
        await self.execute(
            """
            UPDATE support_tickets
            SET admin_answer = ?, status = 'answered'
            WHERE id = ?
            """,
            (answer, ticket_id),
        )

    async def get_mailing_users(self):
        return await self.fetchall(
            "SELECT telegram_id FROM users WHERE is_banned = 0 ORDER BY id ASC"
        )

    async def create_mailing(self, text: str | None, photo_file_id: str | None) -> int:
        return await self.execute(
            """
            INSERT INTO mailings(text, photo_file_id, created_at, sent_count, failed_count)
            VALUES(?, ?, ?, 0, 0)
            """,
            (text, photo_file_id, now_iso()),
        )

    async def update_mailing_result(self, mailing_id: int, sent: int, failed: int) -> None:
        await self.execute(
            "UPDATE mailings SET sent_count = ?, failed_count = ? WHERE id = ?",
            (sent, failed, mailing_id),
        )

    async def get_stats(self) -> dict:
        today_prefix = datetime.now(timezone.utc).date().isoformat()
        total_users = await self.fetchone("SELECT COUNT(*) AS c FROM users")
        today_users = await self.fetchone(
            "SELECT COUNT(*) AS c FROM users WHERE registered_at LIKE ?",
            (f"{today_prefix}%",),
        )
        buy_count = await self.fetchone(
            "SELECT COUNT(*) AS c FROM orders WHERE order_type = 'buy'"
        )
        sell_count = await self.fetchone(
            "SELECT COUNT(*) AS c FROM orders WHERE order_type = 'sell'"
        )
        completed_count = await self.fetchone(
            "SELECT COUNT(*) AS c FROM orders WHERE status = 'completed'"
        )
        rejected_count = await self.fetchone(
            "SELECT COUNT(*) AS c FROM orders WHERE status IN ('rejected', 'cancelled')"
        )
        topup_count = await self.fetchone("SELECT COUNT(*) AS c FROM balance_topups")
        topup_waiting = await self.fetchone("SELECT COUNT(*) AS c FROM balance_topups WHERE status = 'waiting_payment'")
        review_count = await self.fetchone("SELECT COUNT(*) AS c FROM reviews")
        promo_count = await self.fetchone("SELECT COUNT(*) AS c FROM promo_codes")
        balance_sum_row = await self.fetchone("SELECT SUM(CAST(balance AS REAL)) AS s FROM users")
        sums = await self.fetchone(
            """
            SELECT
                SUM(CASE WHEN order_type = 'buy' AND status = 'completed' THEN CAST(total_amount AS REAL) ELSE 0 END) AS buy_sum,
                SUM(CASE WHEN order_type = 'sell' AND status = 'completed' THEN CAST(total_amount AS REAL) ELSE 0 END) AS sell_sum
            FROM orders
            """
        )
        topup_sum = await self.fetchone(
            "SELECT SUM(CASE WHEN status = 'completed' THEN CAST(amount AS REAL) ELSE 0 END) AS s FROM balance_topups"
        )
        buy_sum = float(sums["buy_sum"] or 0)
        sell_sum = float(sums["sell_sum"] or 0)
        return {
            "total_users": int(total_users["c"] or 0),
            "today_users": int(today_users["c"] or 0),
            "buy_count": int(buy_count["c"] or 0),
            "sell_count": int(sell_count["c"] or 0),
            "completed_count": int(completed_count["c"] or 0),
            "rejected_count": int(rejected_count["c"] or 0),
            "buy_sum": buy_sum,
            "sell_sum": sell_sum,
            "gross_profit": buy_sum - sell_sum,
            "topup_count": int(topup_count["c"] or 0),
            "topup_waiting": int(topup_waiting["c"] or 0),
            "topup_sum": float(topup_sum["s"] or 0),
            "review_count": int(review_count["c"] or 0),
            "promo_count": int(promo_count["c"] or 0),
            "balance_sum": float(balance_sum_row["s"] or 0),
        }

    async def get_top_clients(self, limit: int = 10):
        return await self.fetchall(
            """
            SELECT
                users.id, users.telegram_id, users.username, users.first_name, users.balance,
                COUNT(orders.id) AS order_count,
                SUM(CASE WHEN orders.status = 'completed' THEN CAST(orders.total_amount AS REAL) ELSE 0 END) AS total_spent
            FROM users
            LEFT JOIN orders ON orders.user_id = users.id
            GROUP BY users.id
            HAVING order_count > 0
            ORDER BY total_spent DESC
            LIMIT ?
            """,
            (limit,),
        )

    async def get_recent_users(self, limit: int = 10):
        return await self.fetchall(
            "SELECT * FROM users ORDER BY id DESC LIMIT ?",
            (limit,),
        )

    async def get_all_users_count(self) -> int:
        row = await self.fetchone("SELECT COUNT(*) AS c FROM users WHERE is_banned = 0")
        return int(row["c"] or 0)

    async def search_orders(self, query: str, limit: int = 10):
        raw = query.strip().lstrip("#")
        if raw.isdigit():
            return await self.fetchall(
                """
                SELECT orders.*, users.telegram_id, users.username, users.first_name
                FROM orders
                JOIN users ON users.id = orders.user_id
                WHERE orders.id = ?
                LIMIT ?
                """,
                (int(raw), limit),
            )
        return []
