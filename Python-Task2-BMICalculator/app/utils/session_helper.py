"""
app/utils/session_helper.py
Vitals+ uses a lightweight, name-based profile model (no passwords) stored
in a signed Flask session cookie — appropriate for a demo/tracking tool.
This is the single place that reads/writes "who is the current user".
"""

from flask import session

from app.utils.errors import ValidationError


def require_current_username() -> str:
    username = session.get("username")
    if not username:
        raise ValidationError("No active profile. Please complete onboarding first.")
    return username


def set_current_username(username: str) -> None:
    session["username"] = username
    session.permanent = True


def get_current_username():
    return session.get("username")


def clear_current_username() -> None:
    session.pop("username", None)
