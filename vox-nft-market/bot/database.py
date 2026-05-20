import aiosqlite
import time
from bot.config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0,
                sold_count INTEGER DEFAULT 0,
                total_earned REAL DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                created_at REAL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                nft_link TEXT,
                nft_name TEXT,
                collection TEXT,
                rarity TEXT,
                price_ton REAL,
                price_rub REAL,
                status TEXT DEFAULT 'pending',
                owner_before TEXT,
                created_at REAL,
                updated_at REAL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                method TEXT,
                details TEXT,
                status TEXT DEFAULT 'pending',
                created_at REAL,
                updated_at REAL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                rating INTEGER,
                text TEXT,
                created_at REAL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                created_at REAL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.commit()


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def create_user(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, time.time()),
        )
        await db.commit()


async def update_balance(user_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ?, sold_count = sold_count + 1, total_earned = total_earned + ? WHERE user_id = ?",
            (amount, amount, user_id),
        )
        await db.commit()


async def set_balance(user_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = ? WHERE user_id = ?",
            (amount, user_id),
        )
        await db.commit()


async def deduct_balance(user_id: int, amount: float) -> bool:
    user = await get_user(user_id)
    if not user or user["balance"] < amount:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ?",
            (amount, user_id),
        )
        await db.commit()
    return True


async def ban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        await db.commit()


async def unban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        await db.commit()


async def is_banned(user_id: int) -> bool:
    user = await get_user(user_id)
    return bool(user and user["is_banned"])


async def create_deal(
    user_id: int,
    nft_link: str,
    nft_name: str,
    collection: str,
    rarity: str,
    price_ton: float,
    price_rub: float,
    owner_before: str,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO deals
            (user_id, nft_link, nft_name, collection, rarity, price_ton, price_rub, status, owner_before, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'awaiting_transfer', ?, ?, ?)""",
            (user_id, nft_link, nft_name, collection, rarity, price_ton, price_rub, owner_before, time.time(), time.time()),
        )
        await db.commit()
        return cursor.lastrowid


async def get_deal(deal_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM deals WHERE id = ?", (deal_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_deal_status(deal_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE deals SET status = ?, updated_at = ? WHERE id = ?",
            (status, time.time(), deal_id),
        )
        await db.commit()


async def get_deal_by_nft_link(nft_link: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM deals WHERE nft_link = ? AND status NOT IN ('cancelled', 'error')",
            (nft_link,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_deals(user_id: int, limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM deals WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_active_deals() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM deals WHERE status IN ('awaiting_transfer', 'checking') ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def create_withdrawal(user_id: int, amount: float, method: str, details: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO withdrawals (user_id, amount, method, details, status, created_at, updated_at) VALUES (?, ?, ?, ?, 'pending', ?, ?)",
            (user_id, amount, method, details, time.time(), time.time()),
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_withdrawals() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT w.*, u.username FROM withdrawals w JOIN users u ON w.user_id = u.user_id WHERE w.status = 'pending' ORDER BY w.created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_withdrawal_status(withdrawal_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE withdrawals SET status = ?, updated_at = ? WHERE id = ?",
            (status, time.time(), withdrawal_id),
        )
        await db.commit()


async def get_withdrawal(withdrawal_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def add_review(user_id: int, rating: int, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reviews (user_id, rating, text, created_at) VALUES (?, ?, ?, ?)",
            (user_id, rating, text, time.time()),
        )
        await db.commit()


async def get_reviews(limit: int = 10, offset: int = 0) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM reviews ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_reviews_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) as cnt, AVG(rating) as avg_rating FROM reviews")
        row = await cursor.fetchone()
        return {"count": row[0] or 0, "avg_rating": round(row[1] or 0, 1)}


async def add_log(user_id: int, action: str, details: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
            (user_id, action, details, time.time()),
        )
        await db.commit()


async def get_logs(limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM logs ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_all_users(limit: int = 50, offset: int = 0) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE is_banned = 0")
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        users_count = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM deals WHERE status IN ('awaiting_transfer', 'checking')"
        )
        active_deals = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM withdrawals WHERE status = 'pending'")
        pending_withdrawals = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COALESCE(SUM(price_rub), 0) FROM deals WHERE status = 'completed'"
        )
        total_volume = (await cursor.fetchone())[0]

        return {
            "users_count": users_count,
            "active_deals": active_deals,
            "pending_withdrawals": pending_withdrawals,
            "total_volume": round(total_volume, 2),
        }


async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else default


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        await db.commit()


async def get_user_completed_deals_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM deals WHERE user_id = ? AND status = 'completed'",
            (user_id,),
        )
        return (await cursor.fetchone())[0]


async def get_all_deals(limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT d.*, u.username FROM deals d JOIN users u ON d.user_id = u.user_id ORDER BY d.created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
