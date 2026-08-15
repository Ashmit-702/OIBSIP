"""app/routes/analytics.py — GET /api/analytics: charts + stats for the Analytics page."""

from flask import Blueprint, request, jsonify

from app.models import health_repository, goal_repository
from app.services import analytics_service
from app.utils.session_helper import require_current_username

analytics_bp = Blueprint("analytics_api", __name__)


@analytics_bp.route("/api/analytics")
def get_analytics():
    username = require_current_username()
    window = request.args.get("window", "All")

    records = health_repository.get_records(username)
    filtered = analytics_service.filter_by_window(records, window)

    if not filtered:
        return jsonify({"has_data": False}), 200

    goal = goal_repository.get_goal(username)
    goal_weight = goal["target_weight_kg"] if goal else None

    weight_stats = analytics_service.weight_history_stats(filtered)
    weight_series = analytics_service.build_chart_series(filtered, "weight_kg")
    bmi_series = analytics_service.build_chart_series(filtered, "bmi")
    consistency = analytics_service.compute_logging_consistency(filtered)
    weekly_bars = analytics_service.compute_weekly_consistency_bars(records)
    forecast = analytics_service.forecast_trend(filtered, goal_weight_kg=goal_weight)

    return jsonify({
        "has_data": True,
        "window": window,
        "weight_stats": weight_stats,
        "weight_series": weight_series,
        "bmi_series": bmi_series,
        "consistency": consistency,
        "weekly_consistency": weekly_bars,
        "forecast": forecast,
    }), 200
