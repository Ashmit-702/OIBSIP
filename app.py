"""
app.py
Flask entrypoint for the BMI Health Tracker.

Routes:
  GET  /                     -> serves the single-page frontend
  POST /api/calculate        -> calculate BMI, save it, return result + AI insight
  GET  /api/history/<user>   -> return a user's full BMI history (for the trend chart)
  GET  /api/users            -> list all usernames who have saved records
"""

from flask import Flask, request, jsonify, render_template

import db
from bmi_logic import (
    calculate_bmi, classify_bmi, get_ai_insights, ValidationError,
    calculate_ideal_weight_range, calculate_bmr, calculate_daily_calories,
    estimate_body_fat_percent, estimate_water_intake_liters, get_category_info
)

app = Flask(__name__)

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
            "warning": f"Result calculated, but could not be saved: {e}",
            "history": [],
            "ai_insight": {"available": False, "message": "Unavailable because the record wasn't saved."}
        }), 200

    extra_metrics = {"bmr": bmr, "daily_calories": daily_calories, "ideal_weight": ideal_weight}
    ai_insight = get_ai_insights(username, bmi, category, history, extra_metrics)

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
        "ai_insight": ai_insight
    }), 200


@app.route("/api/history/<username>")
def history(username):
    try:
        records = db.get_records(username)
        return jsonify({"history": records}), 200
    except db.DatabaseError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history/<username>", methods=["DELETE"])
def delete_history(username):
    try:
        db.delete_records(username)
        return jsonify({"deleted": True}), 200
    except db.DatabaseError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users")
def users():
    try:
        return jsonify({"users": db.get_all_usernames()}), 200
    except db.DatabaseError as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
