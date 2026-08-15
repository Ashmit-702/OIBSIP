"""
app/services/insight_service.py
Generates plain-language, deterministic insights from a user's actual
history — no LLM involved. This is the primary insight engine; the optional
AI wellness coach (ai_service.py) supplements it but the app is fully
functional and informative without it.
"""

from datetime import date, timedelta
from typing import List

from app.services.analytics_service import compute_logging_consistency, parse_entry_date


def _window(records: list, days: int) -> list:
    cutoff = date.today() - timedelta(days=days)
    return [r for r in records if parse_entry_date(r["entry_date"]) >= cutoff]


def generate_insights(records: list) -> List[str]:
    """Returns a list of short, factual insight strings grounded in real data."""
    insights = []
    if not records:
        return insights

    # 1) Weight change over the last 30 days
    last_30 = _window(records, 30)
    if len(last_30) >= 2:
        change = round(last_30[-1]["weight_kg"] - last_30[0]["weight_kg"], 1)
        if abs(change) >= 0.1:
            direction = "decreased" if change < 0 else "increased"
            insights.append(
                f"Your weight has {direction} by {abs(change)} kg over the last 30 days."
            )
        else:
            insights.append("Your weight has stayed essentially flat over the last 30 days.")

    # 2) Logging consistency, last 14 days
    consistency = compute_logging_consistency(records, window_days=14)
    if consistency["days_logged"] > 0:
        insights.append(
            f"You've logged measurements on {consistency['days_logged']} of the last 14 days."
        )

    # 3) Weekly rate of change this month vs. previous month
    last_30_days = _window(records, 30)
    prev_30_days = [
        r for r in records
        if date.today() - timedelta(days=60) <= parse_entry_date(r["entry_date"]) < date.today() - timedelta(days=30)
    ]
    if len(last_30_days) >= 2 and len(prev_30_days) >= 2:
        recent_rate = (last_30_days[-1]["weight_kg"] - last_30_days[0]["weight_kg"])
        prev_rate = (prev_30_days[-1]["weight_kg"] - prev_30_days[0]["weight_kg"])
        if abs(recent_rate) < abs(prev_rate) - 0.2:
            insights.append("Your rate of weight change has slowed compared with the previous month.")
        elif abs(recent_rate) > abs(prev_rate) + 0.2:
            insights.append("Your rate of weight change has picked up compared with the previous month.")

    # 4) Hydration tracking consistency
    last_14 = _window(records, 14)
    water_logged = sum(1 for r in last_14 if r.get("water_l") is not None)
    if last_14:
        if water_logged >= len(last_14) * 0.7:
            insights.append("You've been consistent about logging your hydration this week.")
        elif water_logged == 0 and len(last_14) >= 3:
            insights.append("You haven't logged hydration recently — add it to your daily check-in to track it.")

    # 5) Activity (steps) logging trend: compare last 7 vs prior 7 days
    last_7 = _window(records, 7)
    prev_7 = [
        r for r in records
        if date.today() - timedelta(days=14) <= parse_entry_date(r["entry_date"]) < date.today() - timedelta(days=7)
    ]
    steps_last_7 = sum(1 for r in last_7 if r.get("steps") is not None)
    steps_prev_7 = sum(1 for r in prev_7 if r.get("steps") is not None)
    if steps_last_7 > steps_prev_7:
        insights.append("Your activity (steps) logging consistency improved this week.")

    # 6) Sleep average note
    sleep_values = [r["sleep_hours"] for r in last_14 if r.get("sleep_hours") is not None]
    if len(sleep_values) >= 3:
        avg_sleep = round(sum(sleep_values) / len(sleep_values), 1)
        if avg_sleep < 6.5:
            insights.append(f"Your average logged sleep this window is {avg_sleep}h — below the typical 7-9h reference range.")
        elif 7 <= avg_sleep <= 9:
            insights.append(f"Your average logged sleep this window is {avg_sleep}h, within the typical 7-9h reference range.")

    return insights
