"""
app/utils/validators.py
Small, focused validation helpers shared by every route. Each raises
ValidationError with a user-facing message on failure, and returns a clean
typed value on success — routes never need to re-derive error messages.
"""

import re
from datetime import datetime, date
from typing import Optional

from app.utils.errors import ValidationError

USERNAME_RE = re.compile(r"^[A-Za-z0-9 _.\-]{1,40}$")
VALID_SEX = {"male", "female"}
VALID_ACTIVITY = {"sedentary", "light", "moderate", "active", "very_active"}
VALID_GOAL_TYPES = {"lose", "maintain", "gain"}


def validate_username(raw) -> str:
    username = (raw or "").strip()
    if not username:
        raise ValidationError("Please enter a name.")
    if not USERNAME_RE.match(username):
        raise ValidationError(
            "Names can only contain letters, numbers, spaces, dots, hyphens, "
            "and underscores (max 40 characters)."
        )
    return username


def validate_positive_number(raw, field_name: str, min_value: float = 0,
                              max_value: Optional[float] = None) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a valid number.")
    if value <= min_value:
        raise ValidationError(f"{field_name} must be greater than {min_value}.")
    if max_value is not None and value > max_value:
        raise ValidationError(f"{field_name} looks too large — please check the value.")
    return value


def validate_optional_positive_number(raw, field_name: str, max_value: Optional[float] = None):
    if raw is None or raw == "":
        return None
    return validate_positive_number(raw, field_name, max_value=max_value)


def validate_height_m(raw) -> float:
    height = validate_positive_number(raw, "Height", min_value=0.3, max_value=2.75)
    return height


def validate_weight_kg(raw) -> float:
    return validate_positive_number(raw, "Weight", min_value=1, max_value=500)


def validate_age(raw) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        age = int(raw)
    except (TypeError, ValueError):
        raise ValidationError("Age must be a whole number.")
    if age <= 0 or age > 120:
        raise ValidationError("Age must be between 1 and 120.")
    return age


def validate_sex(raw) -> Optional[str]:
    if raw is None or raw == "":
        return None
    if raw not in VALID_SEX:
        raise ValidationError("Sex must be 'male' or 'female'.")
    return raw


def validate_activity_level(raw) -> str:
    value = raw or "sedentary"
    if value not in VALID_ACTIVITY:
        raise ValidationError(f"Activity level must be one of: {', '.join(sorted(VALID_ACTIVITY))}.")
    return value


def validate_goal_type(raw) -> str:
    value = raw or "maintain"
    if value not in VALID_GOAL_TYPES:
        raise ValidationError("Goal type must be 'lose', 'maintain', or 'gain'.")
    return value


def validate_date_str(raw, field_name: str = "Date", allow_future: bool = True) -> str:
    if not raw:
        raise ValidationError(f"{field_name} is required.")
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be in YYYY-MM-DD format.")
    if not allow_future and parsed > date.today():
        raise ValidationError(f"{field_name} cannot be in the future.")
    return raw


def validate_optional_date_str(raw, field_name: str = "Date"):
    if not raw:
        return None
    return validate_date_str(raw, field_name, allow_future=True)


def validate_optional_int(raw, field_name: str, min_value: int = 0, max_value: Optional[int] = None):
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a whole number.")
    if value < min_value:
        raise ValidationError(f"{field_name} cannot be negative.")
    if max_value is not None and value > max_value:
        raise ValidationError(f"{field_name} looks too large — please check the value.")
    return value
