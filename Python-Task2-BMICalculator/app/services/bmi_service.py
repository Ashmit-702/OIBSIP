"""
app/services/bmi_service.py
Pure calculation functions for BMI and related metabolic estimates. No I/O,
no Flask imports — trivially unit-testable, ported from the original
project's bmi_logic.py with the same formulas (Mifflin-St Jeor BMR,
Deurenberg body-fat estimate), which are well established and cited inline.
"""

from app.utils.errors import ValidationError

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

CATEGORY_INFO = {
    "Underweight": {
        "blurb": "Your BMI is below the typical healthy range. This can sometimes mean "
                 "your body isn't getting quite enough fuel — nutrient-dense meals and a "
                 "chat with a doctor are worth considering if this is a new change.",
    },
    "Normal": {
        "blurb": "Your BMI falls within the range generally associated with lower health "
                 "risk. Keep doing what's working — consistent movement and balanced meals.",
    },
    "Overweight": {
        "blurb": "Your BMI is a little above the typical range. Small, sustainable changes "
                 "tend to matter more than drastic ones.",
    },
    "Obese": {
        "blurb": "Your BMI is significantly above the typical range, worth discussing with "
                 "a healthcare provider for personalised guidance. BMI alone doesn't capture "
                 "the full picture, but it's a useful starting point.",
    },
}


def calculate_bmi(weight_kg: float, height_m: float) -> float:
    if weight_kg <= 0 or height_m <= 0:
        raise ValidationError("Weight and height must be positive numbers.")
    if height_m > 3:
        raise ValidationError("Height looks too large — please enter height in metres (e.g. 1.75).")
    return round(weight_kg / (height_m ** 2), 2)


def classify_bmi(bmi: float) -> str:
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal"
    elif bmi < 30:
        return "Overweight"
    return "Obese"


def get_category_info(category: str) -> dict:
    return CATEGORY_INFO.get(category, CATEGORY_INFO["Normal"])


def calculate_ideal_weight_range(height_m: float) -> dict:
    """Weight range (kg) corresponding to a 'Normal' BMI of 18.5-24.9 at this height."""
    return {
        "min": round(18.5 * (height_m ** 2), 1),
        "max": round(24.9 * (height_m ** 2), 1),
    }


def calculate_bmr(weight_kg: float, height_m: float, age: int, sex: str) -> float:
    """Mifflin-St Jeor equation. sex expected as 'male' or 'female'."""
    height_cm = height_m * 100
    base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    return round(base + 5, 0) if sex == "male" else round(base - 161, 0)


def calculate_daily_calories(bmr: float, activity_level: str) -> float:
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, ACTIVITY_MULTIPLIERS["sedentary"])
    return round(bmr * multiplier, 0)


def estimate_body_fat_percent(bmi: float, age: int, sex: str) -> float:
    """
    Deurenberg formula — a widely cited estimate of body fat % from BMI, age,
    and sex. An estimate for general wellness tracking, not a clinical
    measurement (which needs calipers, DEXA, or bioimpedance).
    """
    sex_factor = 1 if sex == "male" else 0
    body_fat = (1.20 * bmi) + (0.23 * age) - (10.8 * sex_factor) - 5.4
    return round(max(body_fat, 0), 1)


def estimate_water_intake_target_liters(weight_kg: float) -> float:
    """A common general hydration heuristic: ~33ml per kg of body weight per day."""
    return round(weight_kg * 0.033, 1)
