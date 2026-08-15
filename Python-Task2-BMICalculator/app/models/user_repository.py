"""
app/models/user_repository.py
Data access for user baseline profiles (created during onboarding).

Vitals+ uses a lightweight "named profile" identity model rather than
password-based auth — consistent with the original project and appropriate
for a demo/tracking tool. This is documented clearly in the README; a real
production deployment would add proper authentication in front of this layer.
"""

from datetime import datetime
from typing import Optional

from app.models.db import get_connection, dict_cursor, placeholder, USE_POSTGRES, DatabaseError


def _row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def upsert_profile(username: str, height_m: float, age: Optional[int], sex: Optional[str],
                    activity_level: str, goal_type: str,
                    target_weight_kg: Optional[float], target_date: Optional[str]) -> None:
    now = datetime.utcnow() if USE_POSTGRES else datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            if USE_POSTGRES:
                cur.execute(
                    """INSERT INTO users
                       (username, height_m, age, sex, activity_level, goal_type,
                        target_weight_kg, target_date, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (username) DO UPDATE SET
                         height_m = EXCLUDED.height_m, age = EXCLUDED.age, sex = EXCLUDED.sex,
                         activity_level = EXCLUDED.activity_level, goal_type = EXCLUDED.goal_type,
                         target_weight_kg = EXCLUDED.target_weight_kg,
                         target_date = EXCLUDED.target_date, updated_at = EXCLUDED.updated_at""",
                    (username, height_m, age, sex, activity_level, goal_type,
                     target_weight_kg, target_date, now, now)
                )
            else:
                cur.execute(
                    """INSERT INTO users
                       (username, height_m, age, sex, activity_level, goal_type,
                        target_weight_kg, target_date, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT (username) DO UPDATE SET
                         height_m = excluded.height_m, age = excluded.age, sex = excluded.sex,
                         activity_level = excluded.activity_level, goal_type = excluded.goal_type,
                         target_weight_kg = excluded.target_weight_kg,
                         target_date = excluded.target_date, updated_at = excluded.updated_at""",
                    (username, height_m, age, sex, activity_level, goal_type,
                     target_weight_kg, target_date, now, now)
                )
            conn.commit()
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to save profile: {e}")


def get_profile(username: str) -> Optional[dict]:
    try:
        with get_connection() as conn:
            cur = dict_cursor(conn)
            cur.execute(
                f"SELECT * FROM users WHERE username = {placeholder()}", (username,)
            )
            return _row_to_dict(cur.fetchone())
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to fetch profile: {e}")


def profile_exists(username: str) -> bool:
    return get_profile(username) is not None


def get_all_usernames() -> list:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT username FROM users ORDER BY username ASC")
            return [row[0] for row in cur.fetchall()]
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to fetch users: {e}")


def delete_profile(username: str) -> None:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM users WHERE username = {placeholder()}", (username,))
            conn.commit()
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to delete profile: {e}")
