import aiosqlite
import logging
from contextlib import asynccontextmanager
from config import DB_PATH

logger = logging.getLogger(__name__)

@asynccontextmanager
async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()

async def init_db():
    logger.info("Initializing database schema...")
    async with get_db() as db:
        await db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                is_active BOOLEAN DEFAULT 1,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_pro BOOLEAN DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS job_preferences (
                user_id INTEGER PRIMARY KEY,
                domains TEXT,
                experience_years TEXT,
                work_type TEXT,
                preferred_location TEXT,
                min_salary TEXT,
                max_salary TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                salary TEXT,
                work_type TEXT,
                experience TEXT,
                url TEXT,
                source_portal TEXT,
                domain TEXT,
                score INTEGER DEFAULT 0,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS posted_jobs (
                url TEXT PRIMARY KEY,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS saved_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                job_url TEXT,
                job_title TEXT,
                company TEXT,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                job_url TEXT,
                company TEXT,
                role TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'applied',
                follow_up_sent BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS watched_companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                company_name TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
        ''')
        await db.commit()
    logger.info("Database schema initialized.")

# Basic CRUD Operations

async def add_or_update_user(user_id: int, username: str, full_name: str):
    async with get_db() as db:
        await db.execute('''
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name,
                is_active=1
        ''', (user_id, username, full_name))
        await db.commit()

async def get_user(user_id: int):
    async with get_db() as db:
        async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone()

async def update_job_preferences(user_id: int, domains: str, experience_years: str, work_type: str, preferred_location: str, min_salary: str, max_salary: str):
    async with get_db() as db:
        await db.execute('''
            INSERT INTO job_preferences (user_id, domains, experience_years, work_type, preferred_location, min_salary, max_salary, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                domains=excluded.domains,
                experience_years=excluded.experience_years,
                work_type=excluded.work_type,
                preferred_location=excluded.preferred_location,
                min_salary=excluded.min_salary,
                max_salary=excluded.max_salary,
                updated_at=CURRENT_TIMESTAMP
        ''', (user_id, domains, experience_years, work_type, preferred_location, min_salary, max_salary))
        await db.commit()

async def get_job_preferences(user_id: int):
    async with get_db() as db:
        async with db.execute('SELECT * FROM job_preferences WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone()
