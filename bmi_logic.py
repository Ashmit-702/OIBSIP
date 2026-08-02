"""
bmi_logic.py
Core BMI calculation, category classification, and AI-generated personalized
health insights via the Gemini API.

The Gemini integration is fully optional: if no GEMINI_API_KEY is set, the
app still works perfectly for calculation + history + trends. This means a
missing/invalid key never breaks the core feature.
"""

import os
import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


class ValidationError(Exception):
    """Raised when user input fails validation, so the API can return a 400 with a clear message."""
    pass


def calculate_bmi(weight_kg: float, height_m: float) -> float:
    if weight_kg <= 0 or height_m <= 0:
        raise ValidationError("Weight and height must be positive numbers.")
    if height_m > 3:
        raise ValidationError("Height looks too large — please enter height in metres (e.g. 1.75).")
    bmi = weight_kg / (height_m ** 2)
    return round(bmi, 2)


def classify_bmi(bmi: float) -> str:
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"


def calculate_ideal_weight_range(height_m: float) -> dict:
    """Weight range (kg) corresponding to a 'Normal' BMI of 18.5-24.9 at this height."""
    return {
        "min": round(18.5 * (height_m ** 2), 1),
        "max": round(24.9 * (height_m ** 2), 1)
    }


def calculate_bmr(weight_kg: float, height_m: float, age: int, gender: str) -> float:
    """
    Mifflin-St Jeor equation - the most widely used, clinically validated BMR formula.
    gender expected as 'male' or 'female'.
    """
    height_cm = height_m * 100
    base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    if gender == "male":
        return round(base + 5, 0)
    else:
        return round(base - 161, 0)


ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9
}


def calculate_daily_calories(bmr: float, activity_level: str) -> float:
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, ACTIVITY_MULTIPLIERS["sedentary"])
    return round(bmr * multiplier, 0)


def get_ai_insights(username: str, bmi: float, category: str, history: list,
                     extra_metrics: dict = None) -> dict:
    """
    Calls Gemini to generate a short, personalized, non-alarming health note.
    Returns a dict: {"available": bool, "message": str}
    Never raises — always degrades gracefully so the UI never breaks because
    of an API/network issue.

    extra_metrics (optional): {"bmr": float, "daily_calories": float,
                                "ideal_weight": {"min": float, "max": float}}
    """
    if not GEMINI_API_KEY:
        return {
            "available": False,
            "message": "AI insights are turned off. Add a GEMINI_API_KEY environment "
                       "variable to enable personalized suggestions."
        }

    trend_note = ""
    if len(history) >= 2:
        first_bmi = history[0]["bmi"]
        last_bmi = history[-1]["bmi"]
        direction = "increased" if last_bmi > first_bmi else "decreased" if last_bmi < first_bmi else "stayed steady"
        trend_note = f"Over their {len(history)} logged entries, this user's BMI has {direction} " \
                     f"from {first_bmi} to {last_bmi}."

    metrics_note = ""
    if extra_metrics:
        parts = []
        if extra_metrics.get("bmr"):
            parts.append(f"an estimated BMR of {extra_metrics['bmr']} kcal/day")
        if extra_metrics.get("daily_calories"):
            parts.append(f"an estimated maintenance intake of {extra_metrics['daily_calories']} kcal/day")
        if extra_metrics.get("ideal_weight"):
            iw = extra_metrics["ideal_weight"]
            parts.append(f"a healthy weight range of {iw['min']}-{iw['max']} kg for their height")
        if parts:
            metrics_note = "They also have " + ", ".join(parts) + "."

    prompt = (
        f"You are a friendly, encouraging health assistant inside a BMI tracking app. "
        f"A user named {username} just logged a BMI of {bmi}, classified as '{category}'. "
        f"{trend_note} {metrics_note} "
        f"Write a short (3-4 sentences), warm, non-judgemental note with one practical "
        f"suggestion (diet or activity) suited to this category. Do not give medical "
        f"diagnoses. Do not mention that you are an AI model."
    )

    try:
        response = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return {"available": True, "message": text.strip()}
    except requests.exceptions.Timeout:
        return {"available": False, "message": "AI insight request timed out. Try again in a moment."}
    except requests.exceptions.RequestException as e:
        return {"available": False, "message": f"Could not reach the AI service right now ({e})."}
    except (KeyError, IndexError):
        return {"available": False, "message": "AI service returned an unexpected response."}
