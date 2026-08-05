"""
bmi_logic.py
Core BMI calculation, category classification, and AI-generated personalized
health insights via the Gemini API.

The Gemini integration is fully optional: if no GEMINI_API_KEY is set, the
app still works perfectly for calculation + history + trends. This means a
missing/invalid key never breaks the core feature.
"""

import os
import time
import requests
from datetime import datetime, timedelta

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


LOCAL_TIPS = {
    "Underweight": [
        "adding a nutrient-dense snack (nuts, yoghurt, or a peanut-butter toast) between meals",
        "including a source of protein at every meal to support healthy weight gain",
        "trying strength training 2-3 times a week to build lean mass alongside your meals",
    ],
    "Normal": [
        "keeping up your current mix of balanced meals and regular movement",
        "adding one extra vegetable-rich meal this week to keep the streak going",
        "a brisk 20-30 minute walk most days to maintain your cardiovascular health",
    ],
    "Overweight": [
        "swapping one refined-carb meal a day for a fibre-rich alternative",
        "a 20-minute daily walk — small, repeatable habits tend to stick better than drastic ones",
        "tracking portion sizes for a week just to build awareness, without any strict rules",
    ],
    "Obese": [
        "starting with short, low-impact activity like walking or swimming a few times a week",
        "speaking with a healthcare provider to build a personalised, sustainable plan",
        "focusing on one small, repeatable habit this week rather than an overnight overhaul",
    ],
}


def _local_insight(username: str, bmi: float, category: str, history: list,
                    extra_metrics: dict = None) -> str:
    """
    Deterministic, rule-based fallback used whenever the Gemini API is
    unavailable (no key, rate-limited, network error, etc). This is the
    offline half of the app's Hybrid Insight Engine — it guarantees the
    user always receives a relevant, personalised note instead of an error.
    """
    tip_index = int(bmi * 10) % len(LOCAL_TIPS[category])
    tip = LOCAL_TIPS[category][tip_index]

    trend_clause = ""
    if len(history) >= 2:
        first_bmi = history[0]["bmi"]
        last_bmi = history[-1]["bmi"]
        if last_bmi < first_bmi:
            trend_clause = " Your BMI has trended down since your first entry — nice consistency."
        elif last_bmi > first_bmi:
            trend_clause = " Your BMI has crept up a little since your first entry, worth keeping an eye on."
        else:
            trend_clause = " Your BMI has stayed steady across your logged entries."

    calorie_clause = ""
    if extra_metrics and extra_metrics.get("daily_calories"):
        calorie_clause = f" Based on your details, roughly {round(extra_metrics['daily_calories'])} " \
                          f"kcal/day would maintain your current weight."

    return (
        f"{username}, your BMI of {bmi} falls in the '{category}' range.{trend_clause}"
        f" A good next step could be {tip}.{calorie_clause}"
    )


def get_ai_insights(username: str, bmi: float, category: str, history: list,
                     extra_metrics: dict = None) -> dict:
    """
    Hybrid Insight Engine: tries Gemini first for a richer, LLM-generated note,
    and — if the key is missing, the request times out, or Google returns a
    rate-limit / server error — transparently falls back to a local rule-based
    generator so the user ALWAYS gets a meaningful, personalised note and never
    sees a raw error or any part of an API key.

    Returns: {"available": bool, "message": str, "source": "ai" | "local"}
    Never raises.
    """
    local_message = _local_insight(username, bmi, category, history, extra_metrics)

    if not GEMINI_API_KEY:
        return {"available": True, "message": local_message, "source": "local"}

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

    # Up to 2 attempts total: a fast retry only on rate-limit / transient server errors.
    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=8
            )
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < max_attempts:
                    time.sleep(1.2)
                    continue
                # Exhausted retries — degrade gracefully, no status/key details leaked.
                return {"available": True, "message": local_message, "source": "local"}

            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"available": True, "message": text.strip(), "source": "ai"}

        except requests.exceptions.RequestException:
            # Network error, timeout, DNS failure, etc — never expose exception text
            # (it can contain the request URL, which includes the API key).
            if attempt < max_attempts:
                continue
            return {"available": True, "message": local_message, "source": "local"}
        except (KeyError, IndexError, ValueError):
            return {"available": True, "message": local_message, "source": "local"}

    return {"available": True, "message": local_message, "source": "local"}


def forecast_bmi_trend(history: list, goal_weight_kg: float = None, days_ahead: int = 30) -> dict:
    """
    USP: Predictive BMI Forecasting.

    Fits a simple linear regression (least squares) of BMI over time using the
    user's own logged history, then projects it forward. This is genuinely
    useful (shows where things are headed if nothing changes) and — if a goal
    weight is set — estimates how many days remain at the current rate of
    change, using the same slope translated into kg/day.

    Requires at least 2 entries spanning at least 1 real day; otherwise returns
    {"available": False, "reason": ...} so the UI can hide the card cleanly.
    """
    if len(history) < 2:
        return {"available": False, "reason": "Log at least 2 entries on different days to unlock forecasting."}

    def _parse(raw):
        if isinstance(raw, str):
            return datetime.strptime(raw.split(".")[0], "%Y-%m-%d %H:%M:%S")
        return raw

    points = [(_parse(r["created_at"]), r["bmi"], r["weight_kg"]) for r in history]
    t0 = points[0][0]
    xs = [(p[0] - t0).total_seconds() / 86400.0 for p in points]  # days since first entry

    if max(xs) < 0.5:
        return {"available": False, "reason": "Log entries on at least two different days to unlock forecasting."}

    ys_bmi = [p[1] for p in points]
    ys_weight = [p[2] for p in points]

    def _linreg(xs, ys):
        n = len(xs)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den = sum((x - mean_x) ** 2 for x in xs)
        slope = num / den if den else 0.0
        intercept = mean_y - slope * mean_x
        return slope, intercept

    bmi_slope, bmi_intercept = _linreg(xs, ys_bmi)
    weight_slope, _ = _linreg(xs, ys_weight)

    last_x = xs[-1]
    projected_x = last_x + days_ahead
    projected_bmi = round(bmi_slope * projected_x + bmi_intercept, 2)

    trend_direction = "rising" if bmi_slope > 0.005 else "falling" if bmi_slope < -0.005 else "stable"

    result = {
        "available": True,
        "trend_direction": trend_direction,
        "bmi_change_per_week": round(bmi_slope * 7, 3),
        "projected_bmi": max(projected_bmi, 5),
        "projected_days": days_ahead,
        "confidence": "higher" if len(history) >= 5 else "preliminary",
    }

    if goal_weight_kg and abs(weight_slope) > 0.001:
        current_weight = ys_weight[-1]
        remaining_kg = goal_weight_kg - current_weight
        moving_correct_direction = (remaining_kg > 0 and weight_slope > 0) or \
                                    (remaining_kg < 0 and weight_slope < 0)
        if moving_correct_direction:
            days_needed = abs(remaining_kg / weight_slope)
            eta_date = (datetime.utcnow() + timedelta(days=days_needed)).date().isoformat()
            result["goal_eta_days"] = round(days_needed)
            result["goal_eta_date"] = eta_date
        else:
            result["goal_eta_days"] = None
            result["goal_eta_date"] = None

    return result
