"""app/routes/dashboard.py — GET /api/dashboard, the single summary-card endpoint."""

from datetime import date, timedelta

from flask import Blueprint, jsonify

from app.models import user_repository, health_repository, goal_repository
from app.services import bmi_service, analytics_service, goal_service, score_service, insight_service
from app.utils.session_helper import require_current_username

dashboard_bp = Blueprint("dashboard_api", __name__)


@dashboard_bp.route("/api/dashboard")
def get_dashboard():
    username = require_current_username()
    profile = user_repository.get_profile(username)
    records = health_repository.get_records(username)

    if not records:
        return jsonify({
            "has_data": False,
            "profile": profile,
            "message": "No health records yet. Add your first check-in to start seeing your dashboard.",
        }), 200

    latest = records[-1]
    forecast = analytics_service.forecast_trend(records)
    goal = goal_repository.get_goal(username)

    goal_summary = None
    if goal:
        goal_summary = goal_service.build_goal_summary(records, goal)

    wellness = score_service.compute_wellness_score(
        records, forecast, goal_type=(goal["goal_type"] if goal else "maintain")
    )

    # This month's weight change (for the summary card caption)
    thirty_days_ago = date.today() - timedelta(days=30)
    month_records = [r for r in records if analytics_service.parse_entry_date(r["entry_date"]) >= thirty_days_ago]
    month_change = None
    if len(month_records) >= 2:
        month_change = round(month_records[-1]["weight_kg"] - month_records[0]["weight_kg"], 1)

    consistency = analytics_service.compute_logging_consistency(records)

    today_str = date.today().isoformat()
    today_record = next((r for r in reversed(records) if r["entry_date"] == today_str), None)
    water_target = bmi_service.estimate_water_intake_target_liters(latest["weight_kg"])

    today_progress = {
        "water_l": today_record.get("water_l") if today_record else None,
        "water_target_l": water_target,
        "steps": today_record.get("steps") if today_record else None,
        "steps_target": 8000,
        "sleep_hours": today_record.get("sleep_hours") if today_record else None,
        "logged_today": today_record is not None,
    }

    insights = insight_service.generate_insights(records)[:3]

    return jsonify({
        "has_data": True,
        "profile": profile,
        "bmi": latest["bmi"],
        "category": latest["category"],
        "category_info": bmi_service.get_category_info(latest["category"]),
        "current_weight": latest["weight_kg"],
        "month_change": month_change,
        "goal_summary": goal_summary,
        "wellness_score": wellness,
        "today_progress": today_progress,
        "consistency": consistency,
        "top_insights": insights,
        "forecast": forecast,
    }), 200
