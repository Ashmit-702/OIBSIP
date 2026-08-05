"""
app.py
Flask entrypoint for the BMI Health Tracker.

Routes:
  GET  /                     -> serves the single-page frontend
  POST /api/calculate        -> calculate BMI, save it, return result + AI insight
  GET  /api/history/<user>   -> return a user's full BMI history (for the trend chart)
  GET  /api/users            -> list all usernames who have saved records
"""

from flask import Flask, request, jsonify, render_template, Response

import db
from bmi_logic import (
    calculate_bmi, classify_bmi, get_ai_insights, ValidationError,
    calculate_ideal_weight_range, calculate_bmr, calculate_daily_calories,
    estimate_body_fat_percent, estimate_water_intake_liters, get_category_info,
    compute_streak, compute_achievements, compute_goal_progress, forecast_bmi_trend
)
from report import generate_pdf_report, generate_csv_export

app = Flask(__name__)


def db_error_response(e: db.DatabaseError, status: int = 500):
    """
    Log the full error server-side (useful for debugging on Vercel's logs)
    but return only a generic, safe message to the client — raw DB errors
    can contain connection strings/credentials and must never reach the UI.
    """
    print(f"[db error] {e}")
    return jsonify({"error": "A storage error occurred. Please try again shortly."}), status


# Initialise the database schema once when the app starts.
try:
    db.init_db()
except db.DatabaseError as e:
    # Don't crash the whole app on startup — surface the error per-request instead.
    print(f"[startup warning] {e}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/calculate", methods=["POST"])
def calculate():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    weight_raw = payload.get("weight")
    height_raw = payload.get("height")

    # Optional fields for the richer health dashboard
    age_raw = payload.get("age")
    gender = payload.get("gender")  # "male" or "female", optional
    activity_level = payload.get("activity_level") or "sedentary"

    if not username:
        return jsonify({"error": "Please enter a name to save your record under."}), 400

    try:
        weight_kg = float(weight_raw)
        height_m = float(height_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "Weight and height must be valid numbers."}), 400

    try:
        bmi = calculate_bmi(weight_kg, height_m)
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400

    category = classify_bmi(bmi)
    ideal_weight = calculate_ideal_weight_range(height_m)
    water_intake = estimate_water_intake_liters(weight_kg)
    category_info = get_category_info(category)

    # BMR / calories / body fat are only computed if the user opted to provide age + gender
    bmr = None
    daily_calories = None
    body_fat = None
    age = None
    if age_raw and gender in ("male", "female"):
        try:
            age = int(age_raw)
            if age <= 0 or age > 120:
                raise ValueError
            bmr = calculate_bmr(weight_kg, height_m, age, gender)
            daily_calories = calculate_daily_calories(bmr, activity_level)
            body_fat = estimate_body_fat_percent(bmi, age, gender)
        except (TypeError, ValueError):
            return jsonify({"error": "Age must be a whole number between 1 and 120."}), 400

    try:
        db.add_record(
            username, weight_kg, height_m, bmi, category,
            age=age, gender=gender, activity_level=activity_level,
            bmr=bmr, daily_calories=daily_calories,
            ideal_weight_min=ideal_weight["min"], ideal_weight_max=ideal_weight["max"]
        )
        history = db.get_records(username)
    except db.DatabaseError as e:
        # Log the full error server-side only — never echo raw DB/connection
        # errors to the client, since they can contain connection strings.
        print(f"[db error] {e}")
        return jsonify({
            "bmi": bmi,
            "category": category,
            "category_info": category_info,
            "ideal_weight": ideal_weight,
            "bmr": bmr,
            "daily_calories": daily_calories,
            "body_fat": body_fat,
            "water_intake": water_intake,
            "saved": False,
            "warning": "Result calculated, but could not be saved to your history right now. "
                       "Please try again shortly.",
            "history": [],
            "ai_insight": {"available": False, "message": "Unavailable because the record wasn't saved."},
            "forecast": {"available": False, "reason": "Record wasn't saved."}
        }), 200

    extra_metrics = {"bmr": bmr, "daily_calories": daily_calories, "ideal_weight": ideal_weight}
    ai_insight = get_ai_insights(username, bmi, category, history, extra_metrics)

    streak = compute_streak(history)
    achievements = compute_achievements(history, streak)

    goal_weight = None
    goal_progress = None
    try:
        goal_weight = db.get_goal(username)
        if goal_weight:
            goal_progress = compute_goal_progress(history, goal_weight)
    except db.DatabaseError:
        pass  # goal lookup failing shouldn't break the core calculation response

    forecast = forecast_bmi_trend(history, goal_weight_kg=goal_weight)

    return jsonify({
        "bmi": bmi,
        "category": category,
        "category_info": category_info,
        "ideal_weight": ideal_weight,
        "bmr": bmr,
        "daily_calories": daily_calories,
        "body_fat": body_fat,
        "water_intake": water_intake,
        "saved": True,
        "history": history,
        "ai_insight": ai_insight,
        "streak": streak,
        "achievements": achievements,
        "goal_progress": goal_progress,
        "forecast": forecast
    }), 200


@app.route("/api/history/<username>")
def history(username):
    try:
        records = db.get_records(username)
        return jsonify({"history": records}), 200
    except db.DatabaseError as e:
        return db_error_response(e)


@app.route("/api/history/<username>", methods=["DELETE"])
def delete_history(username):
    try:
        db.delete_records(username)
        return jsonify({"deleted": True}), 200
    except db.DatabaseError as e:
        return db_error_response(e)


@app.route("/api/users")
def users():
    try:
        return jsonify({"users": db.get_all_usernames()}), 200
    except db.DatabaseError as e:
        return db_error_response(e)


@app.route("/api/goal", methods=["POST"])
def set_goal():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    goal_weight = payload.get("goal_weight")

    if not username:
        return jsonify({"error": "Username is required to set a goal."}), 400
    try:
        goal_weight = float(goal_weight)
        if goal_weight <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Goal weight must be a positive number."}), 400

    try:
        db.set_goal(username, goal_weight)
        history = db.get_records(username)
        progress = compute_goal_progress(history, goal_weight) if history else None
        return jsonify({"goal_weight": goal_weight, "progress": progress}), 200
    except db.DatabaseError as e:
        return db_error_response(e)


@app.route("/api/goal/<username>")
def get_goal(username):
    try:
        goal_weight = db.get_goal(username)
        if not goal_weight:
            return jsonify({"goal_weight": None, "progress": None}), 200
        history = db.get_records(username)
        progress = compute_goal_progress(history, goal_weight) if history else None
        return jsonify({"goal_weight": goal_weight, "progress": progress}), 200
    except db.DatabaseError as e:
        return db_error_response(e)


@app.route("/api/community-stats")
def community_stats():
    try:
        return jsonify(db.get_community_stats()), 200
    except db.DatabaseError as e:
        return db_error_response(e)


@app.route("/api/report/<username>")
def download_report(username):
    try:
        history = db.get_records(username)
        if not history:
            return jsonify({"error": "No records found for this user."}), 404

        latest = history[-1]
        goal_weight = db.get_goal(username)
        goal = compute_goal_progress(history, goal_weight) if goal_weight else None

        pdf_bytes = generate_pdf_report(username, latest, history, goal)
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={username}_vitals_report.pdf"}
        )
    except db.DatabaseError as e:
        return db_error_response(e)
    except Exception as e:
        return jsonify({"error": f"Could not generate report: {e}"}), 500


@app.route("/api/export/<username>")
def export_csv(username):
    try:
        history = db.get_records(username)
        if not history:
            return jsonify({"error": "No records found for this user."}), 404

        csv_data = generate_csv_export(history)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={username}_vitals_history.csv"}
        )
    except db.DatabaseError as e:
        return db_error_response(e)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
