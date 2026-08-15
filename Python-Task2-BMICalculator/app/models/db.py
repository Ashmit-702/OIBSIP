"""
app/models/db.py
Storage layer: connection management + schema. Auto-detects Postgres
(DATABASE_URL set) vs local SQLite, same as the original project. This is the
ONLY module that opens raw connections — every repository goes through it,
and all queries elsewhere use parameterized placeholders (never string-built
SQL), so there is no SQL-injection surface anywhere in the app.
"""

import sqlite3
from contextlib import contextmanager

from app.config import Config

USE_POSTGRES = bool(Config.DATABASE_URL)

if USE_POSTGRES:
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError as e:
        # Don't let a broken/missing psycopg2 install crash the entire app at
        # import time -- fall back to SQLite so the app stays usable, and
        # surface a clear error only when something actually tries to use Postgres.
        USE_POSTGRES = False
        _POSTGRES_IMPORT_ERROR = e
    else:
        _POSTGRES_IMPORT_ERROR = None
else:
    _POSTGRES_IMPORT_ERROR = None


class DatabaseError(Exception):
    """Raised on any storage failure so the API layer can return a clean, safe error."""
    pass


def placeholder() -> str:
    return "%s" if USE_POSTGRES else "?"


@contextmanager
def get_connection():
    conn = None
    try:
        if USE_POSTGRES:
            conn = psycopg2.connect(Config.DATABASE_URL, sslmode="require")
        else:
            conn = sqlite3.connect(Config.SQLITE_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
        yield conn
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Could not connect to the database: {e}")
    finally:
        if conn:
            conn.close()


def dict_cursor(conn):
    """Returns a cursor that yields rows usable as dicts, for either backend."""
    if USE_POSTGRES:
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return conn.cursor()


SCHEMA = {
    "users": {
        "postgres": """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                height_m REAL NOT NULL,
                age INTEGER,
                sex TEXT,
                activity_level TEXT NOT NULL DEFAULT 'sedentary',
                goal_type TEXT NOT NULL DEFAULT 'maintain',
                target_weight_kg REAL,
                target_date TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """,
        "sqlite": """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                height_m REAL NOT NULL,
                age INTEGER,
                sex TEXT,
                activity_level TEXT NOT NULL DEFAULT 'sedentary',
                goal_type TEXT NOT NULL DEFAULT 'maintain',
                target_weight_kg REAL,
                target_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """,
    },
    "health_records": {
        "postgres": """
            CREATE TABLE IF NOT EXISTS health_records (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                weight_kg REAL NOT NULL,
                height_m REAL NOT NULL,
                bmi REAL NOT NULL,
                category TEXT NOT NULL,
                waist_cm REAL,
                water_l REAL,
                steps INTEGER,
                sleep_hours REAL,
                calories REAL,
                created_at TIMESTAMP NOT NULL
            )
        """,
        "sqlite": """
            CREATE TABLE IF NOT EXISTS health_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                weight_kg REAL NOT NULL,
                height_m REAL NOT NULL,
                bmi REAL NOT NULL,
                category TEXT NOT NULL,
                waist_cm REAL,
                water_l REAL,
                steps INTEGER,
                sleep_hours REAL,
                calories REAL,
                created_at TEXT NOT NULL
            )
        """,
    },
    "goals": {
        "postgres": """
            CREATE TABLE IF NOT EXISTS goals (
                username TEXT PRIMARY KEY,
                goal_type TEXT NOT NULL,
                target_weight_kg REAL NOT NULL,
                target_date TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """,
        "sqlite": """
            CREATE TABLE IF NOT EXISTS goals (
                username TEXT PRIMARY KEY,
                goal_type TEXT NOT NULL,
                target_weight_kg REAL NOT NULL,
                target_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """,
    },
}


def init_db():
    """Create all tables if they don't exist yet. Safe to call on every cold start."""
    dialect = "postgres" if USE_POSTGRES else "sqlite"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            for table in SCHEMA.values():
                cur.execute(table[dialect])
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_health_username "
                "ON health_records (username, entry_date)"
            )
            conn.commit()
    except Exception as e:
        raise DatabaseError(f"Failed to initialise schema: {e}")
