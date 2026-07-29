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
from bmi_logic import calculate_bmi, classify_bmi, get_ai_insights, ValidationError

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

    try:
        db.add_record(username, weight_kg, height_m, bmi, category)
        history = db.get_records(username)
    except db.DatabaseError as e:
        # Calculation still succeeded even if saving failed — tell the user honestly.
        return jsonify({
            "bmi": bmi,
            "category": category,
            "saved": False,
            "warning": f"Result calculated, but could not be saved: {e}",
            "history": [],
            "ai_insight": {"available": False, "message": "Unavailable because the record wasn't saved."}
        }), 200

    ai_insight = get_ai_insights(username, bmi, category, history)

    return jsonify({
        "bmi": bmi,
        "category": category,
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


@app.route("/api/users")
def users():
    try:
        return jsonify({"users": db.get_all_usernames()}), 200
    except db.DatabaseError as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
