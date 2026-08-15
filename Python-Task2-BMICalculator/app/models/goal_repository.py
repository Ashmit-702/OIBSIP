"""app/models/goal_repository.py — data access for user goals."""

from datetime import datetime
from typing import Optional

from app.models.db import get_connection, dict_cursor, placeholder, USE_POSTGRES, DatabaseError


def set_goal(username: str, goal_type: str, target_weight_kg: float,
             target_date: Optional[str] = None) -> None:
    now = datetime.utcnow() if USE_POSTGRES else datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            if USE_POSTGRES:
                cur.execute(
                    """INSERT INTO goals (username, goal_type, target_weight_kg, target_date,
                                           created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT (username) DO UPDATE SET
                         goal_type = EXCLUDED.goal_type,
                         target_weight_kg = EXCLUDED.target_weight_kg,
                         target_date = EXCLUDED.target_date,
                         updated_at = EXCLUDED.updated_at""",
                    (username, goal_type, target_weight_kg, target_date, now, now)
                )
            else:
                cur.execute(
                    """INSERT INTO goals (username, goal_type, target_weight_kg, target_date,
                                           created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT (username) DO UPDATE SET
                         goal_type = excluded.goal_type,
                         target_weight_kg = excluded.target_weight_kg,
                         target_date = excluded.target_date,
                         updated_at = excluded.updated_at""",
                    (username, goal_type, target_weight_kg, target_date, now, now)
                )
            conn.commit()
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to save goal: {e}")


def get_goal(username: str) -> Optional[dict]:
    try:
        with get_connection() as conn:
            cur = dict_cursor(conn)
            cur.execute(f"SELECT * FROM goals WHERE username = {placeholder()}", (username,))
            row = cur.fetchone()
            return dict(row) if row else None
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to fetch goal: {e}")


def delete_goal(username: str) -> None:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM goals WHERE username = {placeholder()}", (username,))
            conn.commit()
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to delete goal: {e}")
