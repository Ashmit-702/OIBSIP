"""
app/models/health_repository.py
Data access for health_records — the single table backing both "weight
history" and "daily check-ins" (a check-in is just a record with the
optional wellness fields filled in). Keeping one table avoids a redundant
second table for what is really the same timeline of entries.

Every query here is parameterized; no SQL is ever built from raw user input.
"""

from datetime import datetime
from typing import Optional

from app.models.db import get_connection, dict_cursor, placeholder, USE_POSTGRES, DatabaseError


def _rows_to_dicts(rows):
    return [dict(r) for r in rows]


def add_record(username: str, entry_date: str, weight_kg: float, height_m: float,
                bmi: float, category: str, waist_cm: Optional[float] = None,
                water_l: Optional[float] = None, steps: Optional[int] = None,
                sleep_hours: Optional[float] = None, calories: Optional[float] = None) -> int:
    now = datetime.utcnow() if USE_POSTGRES else datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    values = (username, entry_date, weight_kg, height_m, bmi, category,
              waist_cm, water_l, steps, sleep_hours, calories)
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            if USE_POSTGRES:
                cur.execute(
                    """INSERT INTO health_records
                       (username, entry_date, weight_kg, height_m, bmi, category,
                        waist_cm, water_l, steps, sleep_hours, calories, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       RETURNING id""",
                    values + (now,)
                )
                new_id = cur.fetchone()[0]
            else:
                cur.execute(
                    """INSERT INTO health_records
                       (username, entry_date, weight_kg, height_m, bmi, category,
                        waist_cm, water_l, steps, sleep_hours, calories, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    values + (now,)
                )
                new_id = cur.lastrowid
            conn.commit()
            return new_id
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to save health record: {e}")


def get_records(username: str, limit: Optional[int] = None) -> list:
    """All records for a user, oldest -> newest."""
    try:
        with get_connection() as conn:
            cur = dict_cursor(conn)
            sql = (f"SELECT * FROM health_records WHERE username = {placeholder()} "
                   f"ORDER BY entry_date ASC, id ASC")
            cur.execute(sql, (username,))
            rows = _rows_to_dicts(cur.fetchall())
            if limit:
                rows = rows[-limit:]
            return rows
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to fetch records: {e}")


def get_record(username: str, record_id: int) -> Optional[dict]:
    try:
        with get_connection() as conn:
            cur = dict_cursor(conn)
            ph = placeholder()
            cur.execute(
                f"SELECT * FROM health_records WHERE username = {ph} AND id = {ph}",
                (username, record_id)
            )
            row = cur.fetchone()
            return dict(row) if row else None
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to fetch record: {e}")


def update_record(username: str, record_id: int, fields: dict) -> bool:
    """Partial update. fields is a dict of column -> new value."""
    if not fields:
        return False
    allowed = {"entry_date", "weight_kg", "height_m", "bmi", "category", "waist_cm",
               "water_l", "steps", "sleep_hours", "calories"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    ph = placeholder()
    set_clause = ", ".join(f"{col} = {ph}" for col in updates)
    values = list(updates.values()) + [username, record_id]
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE health_records SET {set_clause} "
                f"WHERE username = {ph} AND id = {ph}",
                values
            )
            conn.commit()
            return cur.rowcount > 0
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to update record: {e}")


def delete_record(username: str, record_id: int) -> bool:
    ph = placeholder()
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"DELETE FROM health_records WHERE username = {ph} AND id = {ph}",
                (username, record_id)
            )
            conn.commit()
            return cur.rowcount > 0
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to delete record: {e}")


def delete_all_records(username: str) -> None:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"DELETE FROM health_records WHERE username = {placeholder()}", (username,)
            )
            conn.commit()
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to delete records: {e}")


def get_all_usernames() -> list:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT username FROM health_records ORDER BY username ASC")
            return [row[0] for row in cur.fetchall()]
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to fetch users: {e}")
