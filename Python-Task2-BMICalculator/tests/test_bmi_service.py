"""tests/test_bmi_service.py — BMI formula, classification, and related estimates."""

import pytest

from app.services import bmi_service
from app.utils.errors import ValidationError


class TestCalculateBMI:
    def test_known_value(self):
        # 70 kg / (1.75m)^2 = 22.857...
        assert bmi_service.calculate_bmi(70, 1.75) == 22.86

    def test_formula_matches_definition(self):
        weight, height = 82.4, 1.68
        expected = round(weight / (height ** 2), 2)
        assert bmi_service.calculate_bmi(weight, height) == expected

    def test_zero_weight_rejected(self):
        with pytest.raises(ValidationError):
            bmi_service.calculate_bmi(0, 1.75)

    def test_negative_weight_rejected(self):
        with pytest.raises(ValidationError):
            bmi_service.calculate_bmi(-5, 1.75)

    def test_zero_height_rejected(self):
        with pytest.raises(ValidationError):
            bmi_service.calculate_bmi(70, 0)

    def test_negative_height_rejected(self):
        with pytest.raises(ValidationError):
            bmi_service.calculate_bmi(70, -1.75)

    def test_height_in_cm_rejected(self):
        # Someone typing 175 instead of 1.75 should be caught, not silently computed.
        with pytest.raises(ValidationError):
            bmi_service.calculate_bmi(70, 175)


class TestClassifyBMI:
    def test_underweight_boundary(self):
        assert bmi_service.classify_bmi(18.4) == "Underweight"

    def test_normal_lower_boundary(self):
        assert bmi_service.classify_bmi(18.5) == "Normal"

    def test_normal_upper_boundary(self):
        assert bmi_service.classify_bmi(24.9) == "Normal"

    def test_overweight_boundary(self):
        assert bmi_service.classify_bmi(25.0) == "Overweight"

    def test_overweight_upper_boundary(self):
        assert bmi_service.classify_bmi(29.9) == "Overweight"

    def test_obese_boundary(self):
        assert bmi_service.classify_bmi(30.0) == "Obese"

    def test_very_high_bmi_is_obese(self):
        assert bmi_service.classify_bmi(45.0) == "Obese"

    def test_very_low_bmi_is_underweight(self):
        assert bmi_service.classify_bmi(10.0) == "Underweight"

    @pytest.mark.parametrize("bmi,expected", [
        (17.0, "Underweight"), (18.5, "Normal"), (22.0, "Normal"),
        (24.9, "Normal"), (25.0, "Overweight"), (28.0, "Overweight"),
        (30.0, "Obese"), (35.0, "Obese"),
    ])
    def test_classification_table(self, bmi, expected):
        assert bmi_service.classify_bmi(bmi) == expected


class TestIdealWeightRange:
    def test_range_is_plausible_for_average_height(self):
        result = bmi_service.calculate_ideal_weight_range(1.75)
        assert result["min"] < result["max"]
        assert 50 < result["min"] < 65
        assert 70 < result["max"] < 85


class TestBMR:
    def test_male_formula(self):
        # Mifflin-St Jeor: 10*w + 6.25*h_cm - 5*age + 5
        bmr = bmi_service.calculate_bmr(80, 1.80, 30, "male")
        expected = round((10 * 80) + (6.25 * 180) - (5 * 30) + 5, 0)
        assert bmr == expected

    def test_female_formula(self):
        bmr = bmi_service.calculate_bmr(65, 1.65, 28, "female")
        expected = round((10 * 65) + (6.25 * 165) - (5 * 28) - 161, 0)
        assert bmr == expected

    def test_male_bmr_higher_than_female_same_stats(self):
        male_bmr = bmi_service.calculate_bmr(70, 1.70, 30, "male")
        female_bmr = bmi_service.calculate_bmr(70, 1.70, 30, "female")
        assert male_bmr > female_bmr


class TestDailyCalories:
    def test_activity_multiplier_increases_calories(self):
        bmr = 1600
        sedentary = bmi_service.calculate_daily_calories(bmr, "sedentary")
        active = bmi_service.calculate_daily_calories(bmr, "active")
        assert active > sedentary

    def test_unknown_activity_falls_back_to_sedentary(self):
        bmr = 1600
        default = bmi_service.calculate_daily_calories(bmr, "not_a_real_level")
        sedentary = bmi_service.calculate_daily_calories(bmr, "sedentary")
        assert default == sedentary


class TestWaterIntakeTarget:
    def test_scales_with_weight(self):
        lighter = bmi_service.estimate_water_intake_target_liters(50)
        heavier = bmi_service.estimate_water_intake_target_liters(100)
        assert heavier > lighter
        assert heavier == pytest.approx(3.3, abs=0.1)
