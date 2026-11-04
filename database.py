import aiosqlite
import time

DB_NAME = "data.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cooldowns (
                user_id INTEGER,
                command TEXT,
                last_used REAL,
                PRIMARY KEY (user_id, command)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS economy (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER,
                item_id TEXT,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, item_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                last_xp REAL DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                reason TEXT,
                author_id INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rebirths (
                user_id INTEGER PRIMARY KEY,
                rebirth_level INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def get_cooldown(user_id: int, command: str) -> float:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT last_used FROM cooldowns WHERE user_id = ? AND command = ?",
            (user_id, command),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0.0

async def set_cooldown(user_id: int, command: str, timestamp: float):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO cooldowns (user_id, command, last_used) VALUES (?, ?, ?)
            ON CONFLICT(user_id, command) DO UPDATE SET last_used = excluded.last_used
        """,
            (user_id, command, timestamp),
        )
        await db.commit()

async def get_balance(user_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance FROM economy WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def add_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO economy (user_id, balance) VALUES (?, MAX(0, ?))
            ON CONFLICT(user_id) DO UPDATE SET balance = MAX(0, balance + excluded.balance)
        """, (user_id, amount))
        await db.commit()

async def set_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO economy (user_id, balance) VALUES (?, MAX(0, ?))
            ON CONFLICT(user_id) DO UPDATE SET balance = excluded.balance
        """, (user_id, amount))
        await db.commit()

async def get_inventory(user_id: int) -> dict:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT item_id, quantity FROM inventory WHERE user_id = ? AND quantity > 0", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}

async def add_inventory_item(user_id: int, item_id: str, quantity: int = 1):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity
        """, (user_id, item_id, quantity))
        await db.commit()

async def remove_inventory_item(user_id: int, item_id: str, quantity: int = 1) -> bool:
    current_inv = await get_inventory(user_id)
    if current_inv.get(item_id, 0) < quantity:
        return False

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?
        """, (quantity, user_id, item_id))
        await db.execute("DELETE FROM inventory WHERE quantity <= 0")
        await db.commit()
    return True

async def get_user_level_data(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT xp, level, last_xp FROM levels WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row if row else (0, 0, 0.0)

async def update_user_level_data(user_id: int, xp: int, level: int, last_xp: float):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO levels (user_id, xp, level, last_xp) VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET xp = excluded.xp, level = excluded.level, last_xp = excluded.last_xp
        """, (user_id, xp, level, last_xp))
        await db.commit()

async def add_warn(user_id: int, reason: str, author_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO warns (user_id, reason, author_id) VALUES (?, ?, ?)", (user_id, reason, author_id))
        await db.commit()

async def get_user_rebirth(user_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT rebirth_level FROM rebirths WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def set_user_rebirth(user_id: int, rebirth_level: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO rebirths (user_id, rebirth_level) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET rebirth_level = excluded.rebirth_level
        """, (user_id, rebirth_level))
        await db.commit()