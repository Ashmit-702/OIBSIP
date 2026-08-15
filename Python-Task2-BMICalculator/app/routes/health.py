"""app/routes/health.py — REST API for health_records (weight entries + daily check-ins)."""

from datetime import date

from flask import Blueprint, request, jsonify

from app.models import user_repository, health_repository
from app.services import bmi_service, analytics_service
from app.utils.session_helper import require_current_username
from app.utils.errors import ValidationError, NotFoundError
from app.utils.validators import (
    validate_weight_kg, validate_optional_positive_number, validate_date_str,
    validate_optional_int,
)

health_bp = Blueprint("health_api", __name__)


@health_bp.route("/api/health/history")
def get_history():
    username = require_current_username()
    window = request.args.get("window", "All")
    records = health_repository.get_records(username)
    filtered = analytics_service.filter_by_window(records, window)
    return jsonify({"history": filtered, "count": len(filtered)}), 200


@health_bp.route("/api/health", methods=["POST"])
def create_health_record():
    username = require_current_username()
    profile = user_repository.get_profile(username)
    if not profile:
        raise ValidationError("Complete onboarding before logging a check-in.")

    payload = request.get_json(silent=True) or {}

    weight_kg = validate_weight_kg(payload.get("weight_kg"))
    entry_date = validate_date_str(payload.get("entry_date") or date.today().isoformat(),
                                    "Entry date", allow_future=False)
    waist_cm = validate_optional_positive_number(payload.get("waist_cm"), "Waist measurement", max_value=300)
    water_l = validate_optional_positive_number(payload.get("water_l"), "Water intake", max_value=15)
    steps = validate_optional_int(payload.get("steps"), "Steps", max_value=100000)
    sleep_hours = validate_optional_positive_number(payload.get("sleep_hours"), "Sleep duration", max_value=24)
    calories = validate_optional_positive_number(payload.get("calories"), "Calories", max_value=15000)

    height_m = profile["height_m"]
    bmi = bmi_service.calculate_bmi(weight_kg, height_m)
    category = bmi_service.classify_bmi(bmi)

    new_id = health_repository.add_record(
        username, entry_date, weight_kg, height_m, bmi, category,
        waist_cm=waist_cm, water_l=water_l, steps=steps,
        sleep_hours=sleep_hours, calories=calories,
    )
    record = health_repository.get_record(username, new_id)
    return jsonify({"record": record}), 201


@health_bp.route("/api/health/<int:record_id>", methods=["PUT"])
def update_health_record(record_id):
    username = require_current_username()
    existing = health_repository.get_record(username, record_id)
    if not existing:
        raise NotFoundError("Record not found.")

    payload = request.get_json(silent=True) or {}
    updates = {}

    if "weight_kg" in payload:
        updates["weight_kg"] = validate_weight_kg(payload["weight_kg"])
    if "entry_date" in payload:
        updates["entry_date"] = validate_date_str(payload["entry_date"], "Entry date", allow_future=False)
    if "waist_cm" in payload:
        updates["waist_cm"] = validate_optional_positive_number(payload["waist_cm"], "Waist measurement", max_value=300)
    if "water_l" in payload:
        updates["water_l"] = validate_optional_positive_number(payload["water_l"], "Water intake", max_value=15)
    if "steps" in payload:
        updates["steps"] = validate_optional_int(payload["steps"], "Steps", max_value=100000)
    if "sleep_hours" in payload:
        updates["sleep_hours"] = validate_optional_positive_number(payload["sleep_hours"], "Sleep duration", max_value=24)
    if "calories" in payload:
        updates["calories"] = validate_optional_positive_number(payload["calories"], "Calories", max_value=15000)

    # Recompute BMI/category if weight changed
    if "weight_kg" in updates:
        height_m = existing["height_m"]
        bmi = bmi_service.calculate_bmi(updates["weight_kg"], height_m)
        updates["bmi"] = bmi
        updates["category"] = bmi_service.classify_bmi(bmi)

    health_repository.update_record(username, record_id, updates)
    record = health_repository.get_record(username, record_id)
    return jsonify({"record": record}), 200


@health_bp.route("/api/health/<int:record_id>", methods=["DELETE"])
def delete_health_record(record_id):
    username = require_current_username()
    deleted = health_repository.delete_record(username, record_id)
    if not deleted:
        raise NotFoundError("Record not found.")
    return jsonify({"deleted": True}), 200


@health_bp.route("/api/health/clear", methods=["DELETE"])
def clear_health_history():
    username = require_current_username()
    health_repository.delete_all_records(username)
    return jsonify({"deleted": True}), 200
