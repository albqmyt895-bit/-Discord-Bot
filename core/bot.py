
import aiosqlite
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "data" / "bot.db"


class Database:

    def __init__(self):
        self.connection = None

    async def connect(self):
        DATABASE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.connection = await aiosqlite.connect(
            DATABASE_PATH
        )

        self.connection.row_factory = aiosqlite.Row

        await self.connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                welcome_channel INTEGER,
                log_channel INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await self.connection.commit()

    async def close(self):
        if self.connection:
            await self.connection.close()
            self.connection = None

    async def execute(self, query, parameters=()):
        async with self.connection.execute(
            query, parameters
        ) as cursor:
            await self.connection.commit()
            return cursor.lastrowid

    async def fetchone(self, query, parameters=()):
        async with self.connection.execute(
            query, parameters
        ) as cursor:
            return await cursor.fetchone()

    async def fetchall(self, query, parameters=()):
        async with self.connection.execute(
            query, parameters
        ) as cursor:
            return await cursor.fetchall()
