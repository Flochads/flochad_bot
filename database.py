import aiosqlite
import datetime
import os

DB_NAME = os.getenv("DB_PATH", "activity.db")

async def setup_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                timestamp DATETIME NOT NULL,
                command_type TEXT NOT NULL,
                command_name TEXT NOT NULL
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS kakera_rolls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                timestamp DATETIME NOT NULL,
                value INTEGER NOT NULL
            )
        ''')
        try:
            await db.execute('ALTER TABLE kakera_rolls ADD COLUMN character_name TEXT')
        except aiosqlite.OperationalError:
            pass # Column likely already exists
            
        await db.execute('''
            CREATE TABLE IF NOT EXISTS kakera_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                character_name TEXT NOT NULL,
                value INTEGER NOT NULL,
                timestamp DATETIME NOT NULL
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS topk_alerts (
                id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0
            )
        ''')
        await db.commit()

async def log_activity(guild_id: int, user_id: int, timestamp: datetime.datetime, command_type: str, command_name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO activity_logs (guild_id, user_id, timestamp, command_type, command_name)
            VALUES (?, ?, ?, ?, ?)
        ''', (guild_id, user_id, timestamp.isoformat(), command_type, command_name))
        await db.commit()

async def get_server_stats(guild_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT timestamp FROM activity_logs WHERE guild_id = ?', (guild_id,)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_user_stats(guild_id: int, user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT timestamp FROM activity_logs WHERE guild_id = ? AND user_id = ?', (guild_id, user_id)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_command_stats(guild_id: int, command_name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT timestamp FROM activity_logs WHERE guild_id = ? AND command_name = ?', (guild_id, command_name)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_top_commands(guild_id: int, since: datetime.datetime, limit: int = 10):
    async with aiosqlite.connect(DB_NAME) as db:
        query = '''
            SELECT command_name, COUNT(*) as count 
            FROM activity_logs 
            WHERE guild_id = ? AND timestamp >= ? 
            GROUP BY command_name 
            ORDER BY count DESC 
            LIMIT ?
        '''
        async with db.execute(query, (guild_id, since.isoformat(), limit)) as cursor:
            rows = await cursor.fetchall()
            return rows

async def log_kakera(guild_id: int, timestamp: datetime.datetime, value: int, character_name: str = None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO kakera_rolls (guild_id, timestamp, value, character_name)
            VALUES (?, ?, ?, ?)
        ''', (guild_id, timestamp.isoformat(), value, character_name))
        await db.commit()

async def get_kakera_stats(guild_id: int, since: datetime.datetime, limit: int = 5):
    async with aiosqlite.connect(DB_NAME) as db:
        query1 = '''
            SELECT SUM(value), AVG(value), MAX(value), COUNT(value)
            FROM kakera_rolls
            WHERE guild_id = ? AND timestamp >= ?
        '''
        async with db.execute(query1, (guild_id, since.isoformat())) as cursor:
            row = await cursor.fetchone()

        if row and row[2]: # row[2] is MAX(value)
            query2 = '''
                SELECT character_name, value
                FROM kakera_rolls
                WHERE guild_id = ? AND timestamp >= ?
                ORDER BY value DESC, id DESC LIMIT ?
            '''
            async with db.execute(query2, (guild_id, since.isoformat(), limit)) as cursor:
                top_rolls = await cursor.fetchall()
                return (*row, top_rolls)

        return (*row, []) if row else (None, None, None, 0, [])

async def log_kakera_claim(guild_id: int, user_name: str, character_name: str, value: int, timestamp: datetime.datetime):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO kakera_claims (guild_id, user_name, character_name, value, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (guild_id, user_name, character_name, value, timestamp.isoformat()))
        await db.commit()

async def get_top_claimers(guild_id: int, since: datetime.datetime, limit: int = 5):
    async with aiosqlite.connect(DB_NAME) as db:
        query = '''
            SELECT user_name, character_name, value
            FROM kakera_claims
            WHERE guild_id = ? AND timestamp >= ?
            ORDER BY value DESC, id DESC
            LIMIT ?
        '''
        async with db.execute(query, (guild_id, since.isoformat(), limit)) as cursor:
            return await cursor.fetchall()

async def set_topk_alert_enabled(enabled: bool):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO topk_alerts (id, enabled) VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET enabled = excluded.enabled
        ''', (1 if enabled else 0,))
        await db.commit()

async def get_topk_alert_enabled() -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT enabled FROM topk_alerts WHERE id = 1') as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else False

