"""Tiny SQLite layer for recent-search history.

Uses the stdlib sqlite3 module rather than an ORM — deliberately, since
for a single table like this an ORM would be more machinery than the
problem needs, and it's a chance to show comfort with raw SQL and
parameterized queries (i.e. no string-formatted SQL, ever).
"""

import logging
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

# Serverless platforms like Vercel ship a read-only filesystem except for
# /tmp. Writing station.db next to the source code (fine for a normal
# server) crashes every request on Vercel before it even reaches Flask.
# Detect that case and fall back to /tmp, which is writable but ephemeral
# (wiped between cold starts) — acceptable for a "recent searches" list.
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    DB_PATH = Path(tempfile.gettempdir()) / "station.db"
else:
    DB_PATH = Path(__file__).resolve().parent.parent / "station.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL,
    country TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    searched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pinned_cities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL,
    country TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    pinned_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(city, country)
);
"""


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def record_search(city: str, country: str, lat: float, lon: float) -> None:
    with get_connection() as conn:
        # Drop an existing row for the same place so it moves back to the
        # top of "recent" instead of appearing twice.
        conn.execute(
            "DELETE FROM search_history WHERE city = ? AND country = ?",
            (city, country),
        )
        conn.execute(
            "INSERT INTO search_history (city, country, lat, lon) VALUES (?, ?, ?, ?)",
            (city, country, lat, lon),
        )
        # Keep only the most recent 8 entries.
        conn.execute(
            """
            DELETE FROM search_history
            WHERE id NOT IN (
                SELECT id FROM search_history ORDER BY searched_at DESC LIMIT 8
            )
            """
        )


def recent_searches(limit: int = 8) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT city, country, lat, lon FROM search_history "
            "ORDER BY searched_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def clear_history() -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM search_history")


def pin_city(city: str, country: str, lat: float, lon: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO pinned_cities (city, country, lat, lon) VALUES (?, ?, ?, ?)",
            (city, country, lat, lon),
        )


def unpin_city(city: str, country: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM pinned_cities WHERE city = ? AND country = ?",
            (city, country),
        )


def list_pinned(limit: int = 6) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT city, country, lat, lon FROM pinned_cities ORDER BY pinned_at ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def is_pinned(city: str, country: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM pinned_cities WHERE city = ? AND country = ?",
            (city, country),
        ).fetchone()
        return row is not None
