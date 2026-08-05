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
from datetime import datetime

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


def estimate_body_fat_percent(bmi: float, age: int, gender: str) -> float:
    """
    Deurenberg formula — a widely cited estimate of body fat % from BMI, age, and gender.
    This is an estimate for general wellness tracking, not a clinical measurement
    (which would require calipers, DEXA, or bioelectrical impedance).
    """
    gender_factor = 1 if gender == "male" else 0
    body_fat = (1.20 * bmi) + (0.23 * age) - (10.8 * gender_factor) - 5.4
    return round(max(body_fat, 0), 1)


def estimate_water_intake_liters(weight_kg: float) -> float:
    """A common general hydration heuristic: ~33ml per kg of body weight per day."""
    return round(weight_kg * 0.033, 1)


CATEGORY_INFO = {
    "Underweight": {
        "emoji": "🌱",
        "blurb": "Your BMI suggests you're below the typical healthy range. This can sometimes "
                 "mean your body isn't getting quite enough fuel. Consider nutrient-dense meals "
                 "and speaking with a doctor if this is a new or unexplained change."
    },
    "Normal": {
        "emoji": "✅",
        "blurb": "Your BMI falls within the range generally associated with lower health risk. "
                 "Keep doing what's working — consistent movement and balanced meals."
    },
    "Overweight": {
        "emoji": "⚖️",
        "blurb": "Your BMI is a little above the typical range. Small, sustainable changes — "
                 "a daily walk, more vegetables, better sleep — tend to matter more than drastic ones."
    },
    "Obese": {
        "emoji": "🩺",
        "blurb": "Your BMI is significantly above the typical range, which is worth discussing with "
                 "a healthcare provider for personalized guidance. BMI alone doesn't capture the "
                 "full picture of health, but it's a useful starting point for a conversation."
    }
}


def get_category_info(category: str) -> dict:
    return CATEGORY_INFO.get(category, CATEGORY_INFO["Normal"])


def compute_streak(history: list) -> int:
    """
    Longest run of consecutive calendar days logged, ending at the most recent entry.
    history must be sorted oldest -> newest (as db.get_records returns it).
    """
    if not history:
        return 0

    dates = []
    for record in history:
        raw = record["created_at"]
        d = datetime.strptime(raw.split(".")[0], "%Y-%m-%d %H:%M:%S").date() \
            if isinstance(raw, str) else raw.date()
        if d not in dates:
            dates.append(d)

    dates.sort()
    streak = 1
    best = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            streak += 1
            best = max(best, streak)
        elif (dates[i] - dates[i - 1]).days > 1:
            streak = 1
    return best


ACHIEVEMENTS = [
    {"id": "first_step", "emoji": "🎯", "label": "First Step",
     "condition": lambda h, streak: len(h) >= 1},
    {"id": "consistent", "emoji": "📈", "label": "Consistent Tracker",
     "condition": lambda h, streak: len(h) >= 3},
    {"id": "data_nerd", "emoji": "🔬", "label": "Data Nerd",
     "condition": lambda h, streak: len(h) >= 10},
    {"id": "week_streak", "emoji": "🔥", "label": "7-Day Streak",
     "condition": lambda h, streak: streak >= 7},
    {"id": "healthy_zone", "emoji": "✅", "label": "In the Healthy Zone",
     "condition": lambda h, streak: h and h[-1]["category"] == "Normal"},
]


def compute_achievements(history: list, streak: int) -> list:
    """Returns the list of achievement badges the user has unlocked so far."""
    unlocked = []
    for badge in ACHIEVEMENTS:
        try:
            if badge["condition"](history, streak):
                unlocked.append({"id": badge["id"], "emoji": badge["emoji"], "label": badge["label"]})
        except Exception:
            continue
    return unlocked


def compute_goal_progress(history: list, goal_weight_kg: float) -> dict:
    """
    Progress toward a goal weight, based on the very first logged weight vs the
    most recent one. Works whether the goal is to lose or gain weight.
    Returns {"percent": 0-100, "start_weight": .., "current_weight": .., "goal_weight": ..}
    """
    if not history:
        return None

    start_weight = history[0]["weight_kg"]
    current_weight = history[-1]["weight_kg"]
    total_change_needed = goal_weight_kg - start_weight

    if total_change_needed == 0:
        percent = 100
    else:
        progress_made = current_weight - start_weight
        percent = (progress_made / total_change_needed) * 100
        percent = max(0, min(100, round(percent)))

    return {
        "percent": percent,
        "start_weight": start_weight,
        "current_weight": current_weight,
        "goal_weight": goal_weight_kg
    }


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
