"""
db.py
Storage layer for the BMI Health Tracker.

Design decision: Vercel's serverless functions have an EPHEMERAL filesystem —
a local SQLite file will NOT persist reliably between requests once deployed.
So this module auto-detects its environment:

  - If a DATABASE_URL env var is present (e.g. a free Postgres from Neon,
    Supabase, or Vercel Postgres) -> uses Postgres via psycopg2. Persists
    correctly in production.
  - Otherwise -> falls back to a local SQLite file. Perfect for running on
    your own machine during development and for the demo video.

This means the exact same code works locally out of the box AND is ready
for a real persistent deployment the moment you add a DATABASE_URL.
"""

import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager

# Vercel's project directory is READ-ONLY at runtime — only /tmp is writable.
# Vercel automatically sets the VERCEL env var, so we detect it and redirect
# the SQLite file there. This fixes "unable to open database file" errors.
# Note: /tmp is still ephemeral between cold starts — for real persistence in
# production, set DATABASE_URL to a free Postgres instance (see .env.example).
if os.environ.get("VERCEL"):
    SQLITE_PATH = "/tmp/bmi_records.db"
else:
    SQLITE_PATH = os.path.join(os.path.dirname(__file__), "bmi_records.db")

DATABASE_URL = os.environ.get("DATABASE_URL")  # set this on Vercel for real persistence

USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras


class DatabaseError(Exception):
    """Raised on any storage failure so the API layer can return a clean error to the UI."""
    pass


@contextmanager
def get_connection():
    conn = None
    try:
        if USE_POSTGRES:
            conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        else:
            conn = sqlite3.connect(SQLITE_PATH)
            conn.row_factory = sqlite3.Row
        yield conn
    except Exception as e:
        raise DatabaseError(f"Could not connect to the database: {e}")
    finally:
        if conn:
            conn.close()


def init_db():
    """Create the records table if it doesn't exist yet. Safe to call on every cold start."""
    ddl_postgres = """
        CREATE TABLE IF NOT EXISTS bmi_records (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            weight_kg REAL NOT NULL,
            height_m REAL NOT NULL,
            bmi REAL NOT NULL,
            category TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            activity_level TEXT,
            bmr REAL,
            daily_calories REAL,
            ideal_weight_min REAL,
            ideal_weight_max REAL,
            created_at TIMESTAMP NOT NULL
        )
    """
    ddl_sqlite = """
        CREATE TABLE IF NOT EXISTS bmi_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            weight_kg REAL NOT NULL,
            height_m REAL NOT NULL,
            bmi REAL NOT NULL,
            category TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            activity_level TEXT,
            bmr REAL,
            daily_calories REAL,
            ideal_weight_min REAL,
            ideal_weight_max REAL,
            created_at TEXT NOT NULL
        )
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(ddl_postgres if USE_POSTGRES else ddl_sqlite)
            conn.commit()
    except Exception as e:
        raise DatabaseError(f"Failed to initialise schema: {e}")


def add_record(username: str, weight_kg: float, height_m: float, bmi: float, category: str,
                age=None, gender=None, activity_level=None, bmr=None,
                daily_calories=None, ideal_weight_min=None, ideal_weight_max=None):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            now = datetime.utcnow()
            values = (username, weight_kg, height_m, bmi, category, age, gender,
                      activity_level, bmr, daily_calories, ideal_weight_min, ideal_weight_max)
            if USE_POSTGRES:
                cur.execute(
                    """INSERT INTO bmi_records
                       (username, weight_kg, height_m, bmi, category, age, gender,
                        activity_level, bmr, daily_calories, ideal_weight_min, ideal_weight_max, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    values + (now,)
                )
            else:
                cur.execute(
                    """INSERT INTO bmi_records
                       (username, weight_kg, height_m, bmi, category, age, gender,
                        activity_level, bmr, daily_calories, ideal_weight_min, ideal_weight_max, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    values + (now.strftime("%Y-%m-%d %H:%M:%S"),)
                )
            conn.commit()
    except Exception as e:
        raise DatabaseError(f"Failed to save record: {e}")


def get_records(username: str):
    """Return all records for a user, oldest -> newest, as a list of plain dicts."""
    try:
        with get_connection() as conn:
            if USE_POSTGRES:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    "SELECT * FROM bmi_records WHERE username = %s ORDER BY created_at ASC",
                    (username,)
                )
                rows = cur.fetchall()
                return [dict(r) for r in rows]
            else:
                cur = conn.cursor()
                cur.execute(
                    "SELECT * FROM bmi_records WHERE username = ? ORDER BY created_at ASC",
                    (username,)
                )
                rows = cur.fetchall()
                return [dict(r) for r in rows]
    except Exception as e:
        raise DatabaseError(f"Failed to fetch records: {e}")


def get_all_usernames():
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT username FROM bmi_records ORDER BY username ASC")
            return [row[0] for row in cur.fetchall()]
    except Exception as e:
        raise DatabaseError(f"Failed to fetch users: {e}")


def delete_records(username: str):
    """Delete all records for a user. Used by the 'Clear my history' action."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            placeholder = "%s" if USE_POSTGRES else "?"
            cur.execute(f"DELETE FROM bmi_records WHERE username = {placeholder}", (username,))
            conn.commit()
    except Exception as e:
        raise DatabaseError(f"Failed to delete records: {e}")
