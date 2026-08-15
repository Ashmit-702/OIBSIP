"""app/routes/goals.py — GET/POST /api/goals."""

from flask import Blueprint, request, jsonify

from app.models import goal_repository, health_repository
from app.services import goal_service
from app.utils.session_helper import require_current_username
from app.utils.validators import validate_goal_type, validate_positive_number, validate_optional_date_str

goals_bp = Blueprint("goals_api", __name__)


@goals_bp.route("/api/goals", methods=["GET"])
def get_goal():
    username = require_current_username()
    goal = goal_repository.get_goal(username)
    if not goal:
        return jsonify({"goal": None}), 200

    records = health_repository.get_records(username)
    summary = goal_service.build_goal_summary(records, goal) if records else None
    return jsonify({"goal": goal, "summary": summary}), 200


@goals_bp.route("/api/goals", methods=["POST"])
def set_goal():
    username = require_current_username()
    payload = request.get_json(silent=True) or {}

    goal_type = validate_goal_type(payload.get("goal_type"))
    target_weight = validate_positive_number(payload.get("target_weight_kg"), "Target weight", max_value=500)
    target_date = validate_optional_date_str(payload.get("target_date"), "Target date")

    goal_repository.set_goal(username, goal_type, target_weight, target_date)
    goal = goal_repository.get_goal(username)

    records = health_repository.get_records(username)
    summary = goal_service.build_goal_summary(records, goal) if records else None
    return jsonify({"goal": goal, "summary": summary}), 200


@goals_bp.route("/api/goals", methods=["DELETE"])
def delete_goal():
    username = require_current_username()
    goal_repository.delete_goal(username)
    return jsonify({"deleted": True}), 200
