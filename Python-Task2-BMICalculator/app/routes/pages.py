"""app/routes/pages.py — server-rendered page routes (no business logic here)."""

from flask import Blueprint, render_template, redirect, url_for, request

from app.models import user_repository, health_repository, goal_repository
from app.services.demo_service import seed_demo_data, DEMO_USERNAME
from app.utils.session_helper import get_current_username, set_current_username, clear_current_username
from app.utils.validators import (
    validate_username, validate_height_m, validate_age, validate_sex,
    validate_activity_level, validate_goal_type, validate_optional_positive_number,
    validate_optional_date_str,
)
from app.utils.errors import ValidationError

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def landing():
    if get_current_username():
        return redirect(url_for("pages.dashboard"))
    known_users = user_repository.get_all_usernames()
    return render_template("landing.html", known_users=known_users)


@pages_bp.route("/demo")
def demo():
    seed_demo_data()
    set_current_username(DEMO_USERNAME)
    return redirect(url_for("pages.dashboard"))


@pages_bp.route("/onboarding", methods=["GET", "POST"])
def onboarding():
    if request.method == "GET":
        known_users = user_repository.get_all_usernames()
        return render_template("onboarding.html", known_users=known_users, error=None)

    form = request.form
    try:
        username = validate_username(form.get("username"))
        height_m = validate_height_m(form.get("height_m"))
        age = validate_age(form.get("age"))
        sex = validate_sex(form.get("sex"))
        activity_level = validate_activity_level(form.get("activity_level"))
        goal_type = validate_goal_type(form.get("goal_type"))
        current_weight = validate_optional_positive_number(form.get("current_weight"), "Current weight")
        target_weight = validate_optional_positive_number(form.get("target_weight"), "Target weight")
        target_date = validate_optional_date_str(form.get("target_date"), "Target date")
    except ValidationError as e:
        known_users = user_repository.get_all_usernames()
        return render_template("onboarding.html", known_users=known_users, error=str(e)), 400

    user_repository.upsert_profile(
        username, height_m, age, sex, activity_level, goal_type, target_weight, target_date
    )

    if goal_type != "maintain" and target_weight:
        goal_repository.set_goal(username, goal_type, target_weight, target_date)

    if current_weight:
        from app.services.bmi_service import calculate_bmi, classify_bmi
        from datetime import date
        bmi = calculate_bmi(current_weight, height_m)
        category = classify_bmi(bmi)
        health_repository.add_record(username, date.today().isoformat(), current_weight,
                                      height_m, bmi, category)

    set_current_username(username)
    return redirect(url_for("pages.dashboard"))


@pages_bp.route("/switch-profile", methods=["POST"])
def switch_profile():
    """Returning user picking their existing name from the landing/onboarding page."""
    username = (request.form.get("username") or "").strip()
    if username and user_repository.profile_exists(username):
        set_current_username(username)
        return redirect(url_for("pages.dashboard"))
    return redirect(url_for("pages.onboarding"))


@pages_bp.route("/logout")
def logout():
    clear_current_username()
    return redirect(url_for("pages.landing"))


def _require_profile():
    """Returns username if a profile is active, otherwise None."""
    username = get_current_username()
    if not username or not user_repository.profile_exists(username):
        return None
    return username


@pages_bp.route("/dashboard")
def dashboard():
    username = _require_profile()
    if not username:
        return redirect(url_for("pages.onboarding"))
    return render_template("dashboard.html", username=username)


@pages_bp.route("/analytics")
def analytics():
    username = _require_profile()
    if not username:
        return redirect(url_for("pages.onboarding"))
    return render_template("analytics.html", username=username)


@pages_bp.route("/goals")
def goals():
    username = _require_profile()
    if not username:
        return redirect(url_for("pages.onboarding"))
    return render_template("goals.html", username=username)


@pages_bp.route("/history")
def history():
    username = _require_profile()
    if not username:
        return redirect(url_for("pages.onboarding"))
    return render_template("history.html", username=username)


@pages_bp.route("/reports")
def reports():
    username = _require_profile()
    if not username:
        return redirect(url_for("pages.onboarding"))
    return render_template("reports.html", username=username)
