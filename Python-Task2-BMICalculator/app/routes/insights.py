"""app/routes/insights.py — GET /api/insights."""

from flask import Blueprint, jsonify

from app.models import health_repository, goal_repository
from app.services import insight_service, analytics_service, ai_service
from app.utils.session_helper import require_current_username

insights_bp = Blueprint("insights_api", __name__)


@insights_bp.route("/api/insights")
def get_insights():
    username = require_current_username()
    records = health_repository.get_records(username)

    if not records:
        return jsonify({"has_data": False, "insights": [], "ai_note": None}), 200

    insights = insight_service.generate_insights(records)

    # Build a small structured metrics summary for the optional AI coach —
    # never the raw database rows.
    latest = records[-1]
    forecast = analytics_service.forecast_trend(records)
    goal = goal_repository.get_goal(username)
    goal_progress_pct = None
    if goal:
        from app.services.goal_service import compute_goal_progress
        progress = compute_goal_progress(records, goal["target_weight_kg"])
        goal_progress_pct = progress["percent"] if progress else None

    recent_sleep = [r["sleep_hours"] for r in records[-7:] if r.get("sleep_hours") is not None]
    recent_water = [r["water_l"] for r in records[-7:] if r.get("water_l") is not None]

    metrics = {
        "bmi": latest["bmi"],
        "bmi_category": latest["category"],
        "weight_trend_direction": forecast.get("trend_direction") if forecast.get("available") else None,
        "weight_change_per_week_kg": forecast.get("weight_change_per_week") if forecast.get("available") else None,
        "avg_sleep_hours_last_7_days": round(sum(recent_sleep) / len(recent_sleep), 1) if recent_sleep else None,
        "avg_water_l_last_7_days": round(sum(recent_water) / len(recent_water), 1) if recent_water else None,
        "goal_progress_percent": goal_progress_pct,
    }
    ai_note = ai_service.get_ai_wellness_note(metrics)

    return jsonify({"has_data": True, "insights": insights, "ai_note": ai_note}), 200
