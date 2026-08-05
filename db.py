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
    """Create tables if they don't exist yet. Safe to call on every cold start."""
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
    ddl_goals_postgres = """
        CREATE TABLE IF NOT EXISTS user_goals (
            username TEXT PRIMARY KEY,
            goal_weight_kg REAL NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
    """
    ddl_goals_sqlite = """
        CREATE TABLE IF NOT EXISTS user_goals (
            username TEXT PRIMARY KEY,
            goal_weight_kg REAL NOT NULL,
            updated_at TEXT NOT NULL
        )
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(ddl_postgres if USE_POSTGRES else ddl_sqlite)
            cur.execute(ddl_goals_postgres if USE_POSTGRES else ddl_goals_sqlite)
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


def set_goal(username: str, goal_weight_kg: float):
    """Upsert a user's goal weight."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            now = datetime.utcnow()
            if USE_POSTGRES:
                cur.execute(
                    """INSERT INTO user_goals (username, goal_weight_kg, updated_at)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (username) DO UPDATE
                       SET goal_weight_kg = EXCLUDED.goal_weight_kg, updated_at = EXCLUDED.updated_at""",
                    (username, goal_weight_kg, now)
                )
            else:
                cur.execute(
                    """INSERT INTO user_goals (username, goal_weight_kg, updated_at)
                       VALUES (?, ?, ?)
                       ON CONFLICT (username) DO UPDATE
                       SET goal_weight_kg = excluded.goal_weight_kg, updated_at = excluded.updated_at""",
                    (username, goal_weight_kg, now.strftime("%Y-%m-%d %H:%M:%S"))
                )
            conn.commit()
    except Exception as e:
        raise DatabaseError(f"Failed to save goal: {e}")


def get_goal(username: str):
    """Return the goal weight (kg) for a user, or None if no goal is set."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            placeholder = "%s" if USE_POSTGRES else "?"
            cur.execute(f"SELECT goal_weight_kg FROM user_goals WHERE username = {placeholder}", (username,))
            row = cur.fetchone()
            if row is None:
                return None
            return row[0]
    except Exception as e:
        raise DatabaseError(f"Failed to fetch goal: {e}")


def get_community_stats():
    """Aggregate, anonymous stats across ALL users — no individual data exposed."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*), COUNT(DISTINCT username), AVG(bmi) FROM bmi_records")
            row = cur.fetchone()
            total_entries = row[0] or 0
            distinct_users = row[1] or 0
            avg_bmi = round(row[2], 1) if row[2] is not None else None
            return {
                "total_entries": total_entries,
                "distinct_users": distinct_users,
                "average_bmi": avg_bmi
            }
    except Exception as e:
        raise DatabaseError(f"Failed to fetch community stats: {e}")
