"""tests/test_validators.py — input validation edge cases."""

import pytest

from app.utils import validators
from app.utils.errors import ValidationError


class TestUsername:
    def test_valid_username_passes(self):
        assert validators.validate_username("Alex Smith") == "Alex Smith"

    def test_empty_username_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_username("")

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_username("   ")

    def test_special_characters_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_username("Robert'); DROP TABLE users;--")

    def test_too_long_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_username("a" * 41)


class TestWeightHeight:
    def test_valid_weight(self):
        assert validators.validate_weight_kg("70.5") == 70.5

    def test_non_numeric_weight_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_weight_kg("abc")

    def test_zero_weight_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_weight_kg("0")

    def test_negative_weight_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_weight_kg("-10")

    def test_absurd_weight_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_weight_kg("99999")

    def test_valid_height(self):
        assert validators.validate_height_m("1.75") == 1.75

    def test_height_in_cm_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_height_m("175")

    def test_negative_height_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_height_m("-1.75")


class TestAge:
    def test_valid_age(self):
        assert validators.validate_age("30") == 30

    def test_none_age_is_optional(self):
        assert validators.validate_age(None) is None
        assert validators.validate_age("") is None

    def test_non_integer_age_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_age("thirty")

    def test_zero_age_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_age("0")

    def test_too_large_age_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_age("200")


class TestSexActivityGoal:
    def test_valid_sex(self):
        assert validators.validate_sex("male") == "male"
        assert validators.validate_sex("female") == "female"

    def test_invalid_sex_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_sex("robot")

    def test_default_activity_level(self):
        assert validators.validate_activity_level(None) == "sedentary"

    def test_invalid_activity_level_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_activity_level("superhuman")

    def test_default_goal_type(self):
        assert validators.validate_goal_type(None) == "maintain"

    def test_invalid_goal_type_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_goal_type("teleport")


class TestDates:
    def test_valid_date(self):
        assert validators.validate_date_str("2026-01-15") == "2026-01-15"

    def test_missing_date_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_date_str(None)

    def test_malformed_date_rejected(self):
        with pytest.raises(ValidationError):
            validators.validate_date_str("15-01-2026")

    def test_future_date_rejected_when_disallowed(self):
        with pytest.raises(ValidationError):
            validators.validate_date_str("2099-01-01", allow_future=False)

    def test_optional_date_none_passes(self):
        assert validators.validate_optional_date_str(None) is None
        assert validators.validate_optional_date_str("") is None


class TestOptionalNumbers:
    def test_optional_positive_number_none_passes(self):
        assert validators.validate_optional_positive_number(None, "Steps") is None

    def test_optional_positive_number_rejects_negative(self):
        with pytest.raises(ValidationError):
            validators.validate_optional_positive_number("-5", "Water")

    def test_optional_int_within_bounds(self):
        assert validators.validate_optional_int("8000", "Steps", max_value=100000) == 8000

    def test_optional_int_rejects_non_integer(self):
        with pytest.raises(ValidationError):
            validators.validate_optional_int("8.5k", "Steps")
