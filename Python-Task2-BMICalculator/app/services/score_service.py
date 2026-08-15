"""
app/services/score_service.py
Computes the "Wellness Consistency Score" — a transparent, deterministic
0-100 metric built entirely from the user's own logged data. This is
explicitly NOT a medically validated health score; it is a custom tracking
metric meant to reward consistent logging and a healthy trend direction,
with every point traceable to a named component.

Weights (redistributed proportionally if a component has no data at all,
so the score always totals out of 100):
  - BMI standing        (25): how close the latest BMI sits to the center
                                of the healthy range (~21.7)
  - Weight trend         (20): whether the regression-fit trend is moving
                                the right way for the user's goal
  - Logging consistency  (20): days logged in the trailing 30 days
  - Hydration tracking   (15): average logged water intake vs. a
                                weight-based target
  - Sleep tracking        (10): average logged sleep vs. a 7-9h reference
  - Activity logging      (10): share of recent entries with steps logged
"""

from typing import Optional

from app.services.analytics_service import compute_logging_consistency
from app.services.bmi_service import estimate_water_intake_target_liters


def _bmi_standing_score(bmi: float) -> float:
    center = 21.7
    diff = abs(bmi - center)
    return round(max(0.0, min(25.0, 25 - diff * 2)), 1)


def _weight_trend_score(forecast: dict, goal_type: str) -> float:
    if not forecast or not forecast.get("available"):
        return 10.0  # neutral — not enough history yet
    direction = forecast.get("trend_direction")
    desired = {"lose": "falling", "gain": "rising", "maintain": "stable"}.get(goal_type, "stable")
    if direction == desired:
        return 20.0
    if direction == "stable":
        return 12.0
    return 5.0


def _hydration_score(records: list, weight_kg: float) -> Optional[float]:
    logged = [r["water_l"] for r in records[-14:] if r.get("water_l") is not None]
    if not logged:
        return None
    target = estimate_water_intake_target_liters(weight_kg)
    avg = sum(logged) / len(logged)
    ratio = min(1.0, avg / target) if target else 0
    return round(ratio * 15, 1)


def _sleep_score(records: list) -> Optional[float]:
    logged = [r["sleep_hours"] for r in records[-14:] if r.get("sleep_hours") is not None]
    if not logged:
        return None
    avg = sum(logged) / len(logged)
    if 7 <= avg <= 9:
        return 10.0
    diff = min(abs(avg - 7), abs(avg - 9))
    return round(max(0.0, 10 - diff * 2.5), 1)


def _activity_logging_score(records: list) -> Optional[float]:
    recent = records[-14:]
    if not recent:
        return None
    logged = sum(1 for r in recent if r.get("steps") is not None)
    return round((logged / len(recent)) * 10, 1)


def compute_wellness_score(records: list, forecast: dict, goal_type: str = "maintain") -> Optional[dict]:
    if not records:
        return None

    latest = records[-1]
    bmi_score = _bmi_standing_score(latest["bmi"])
    trend_score = _weight_trend_score(forecast, goal_type)
    consistency = compute_logging_consistency(records)
    consistency_score = round((consistency["percent"] / 100) * 20, 1)
    hydration_score = _hydration_score(records, latest["weight_kg"])
    sleep_score = _sleep_score(records)
    activity_score = _activity_logging_score(records)

    components = [
        {"label": "BMI standing", "score": bmi_score, "max": 25},
        {"label": "Weight trend", "score": trend_score, "max": 20},
        {"label": "Logging consistency", "score": consistency_score, "max": 20},
    ]
    if hydration_score is not None:
        components.append({"label": "Hydration tracking", "score": hydration_score, "max": 15})
    if sleep_score is not None:
        components.append({"label": "Sleep tracking", "score": sleep_score, "max": 10})
    if activity_score is not None:
        components.append({"label": "Activity logging", "score": activity_score, "max": 10})

    weight_total = sum(c["max"] for c in components)
    raw_sum = sum(c["score"] for c in components)
    final_score = max(0, min(100, round(raw_sum / weight_total * 100))) if weight_total else 0

    return {"score": final_score, "components": components}
