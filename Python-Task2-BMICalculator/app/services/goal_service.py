"""
app/services/goal_service.py
Turns a goal (goal_type, target_weight_kg, target_date) plus a user's logged
history into progress percentage, required pace, and an estimated completion
date. Deliberately does NOT prescribe a weight-loss/gain rate — it only
reports the pace implied by the target date and the pace the user is
actually on, so the person can see the gap for themselves.
"""

from datetime import date, datetime
from typing import Optional

from app.services.analytics_service import forecast_trend

# A conservative, widely-cited "avoid" ceiling for weight change discourse —
# used only to flag pacing that looks unusually fast, never to recommend one.
CAUTION_WEEKLY_KG = 1.0


def compute_goal_progress(records: list, target_weight_kg: float) -> Optional[dict]:
    """Progress from the user's first logged weight toward the goal weight."""
    if not records:
        return None

    start_weight = records[0]["weight_kg"]
    current_weight = records[-1]["weight_kg"]
    total_change_needed = target_weight_kg - start_weight

    if total_change_needed == 0:
        percent = 100
    else:
        progress_made = current_weight - start_weight
        percent = max(0, min(100, round((progress_made / total_change_needed) * 100)))

    return {
        "percent": percent,
        "start_weight": start_weight,
        "current_weight": current_weight,
        "target_weight": target_weight_kg,
        "remaining_kg": round(target_weight_kg - current_weight, 1),
    }


def compute_required_pace(records: list, target_weight_kg: float,
                           target_date: Optional[str]) -> Optional[dict]:
    """Weekly kg change required to hit target_weight_kg by target_date."""
    if not records or not target_date:
        return None
    current_weight = records[-1]["weight_kg"]
    try:
        target = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        return None

    days_remaining = (target - date.today()).days
    if days_remaining <= 0:
        return {"weekly_kg_required": None, "days_remaining": days_remaining, "feasible": False}

    remaining_kg = target_weight_kg - current_weight
    weekly_required = round((remaining_kg / days_remaining) * 7, 2)

    return {
        "weekly_kg_required": weekly_required,
        "days_remaining": days_remaining,
        "feasible": abs(weekly_required) <= CAUTION_WEEKLY_KG,
    }


def estimate_completion(records: list, target_weight_kg: float) -> dict:
    """Estimated completion date based on the user's actual current trend (regression)."""
    forecast = forecast_trend(records, goal_weight_kg=target_weight_kg)
    if not forecast.get("available"):
        return {"available": False, "reason": forecast.get("reason", "Not enough data yet.")}
    return {
        "available": True,
        "eta_date": forecast.get("goal_eta_date"),
        "eta_days": forecast.get("goal_eta_days"),
        "current_weekly_rate": forecast.get("weight_change_per_week"),
        "trend_direction": forecast.get("trend_direction"),
    }


def build_goal_summary(records: list, goal: dict) -> dict:
    """Combines progress + pace + ETA into one payload for the Goals page."""
    target_weight = goal["target_weight_kg"]
    progress = compute_goal_progress(records, target_weight)
    pace = compute_required_pace(records, target_weight, goal.get("target_date"))
    completion = estimate_completion(records, target_weight)
    return {
        "goal_type": goal["goal_type"],
        "target_weight_kg": target_weight,
        "target_date": goal.get("target_date"),
        "progress": progress,
        "required_pace": pace,
        "estimated_completion": completion,
    }
