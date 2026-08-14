"""Station — Flask backend for a weather instrument-panel web app.

Run with:
    python app.py

Requires an OPENWEATHER_API_KEY in the environment (or a .env file —
see .env.example). The key never reaches the browser: the frontend
only ever talks to this server's /api/* routes.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from services import db
from services.exceptions import WeatherServiceError
from services.weather_service import get_weather

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("station")

app = Flask(__name__)
API_KEY = os.environ.get("OPENWEATHER_API_KEY", "").strip()

try:
    db.init_db()
    DB_AVAILABLE = True
except Exception:
    # Search history is a nice-to-have. If the filesystem is read-only
    # (or anything else about the DB setup fails), log it and keep serving
    # weather lookups instead of crashing the whole app on cold start.
    logger.exception("Could not initialize the search-history database; continuing without it.")
    DB_AVAILABLE = False


@app.route("/")
def index():
    return render_template("index.html", has_api_key=bool(API_KEY))


@app.route("/api/weather")
def api_weather():
    city = request.args.get("city", "").strip() or None
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    units = request.args.get("units", "metric")

    if units not in ("metric", "imperial"):
        return jsonify({"error": "units must be 'metric' or 'imperial'"}), 400
    if not city and (lat is None or lon is None):
        return jsonify({"error": "Provide either ?city= or both ?lat= and ?lon="}), 400

    try:
        data = get_weather(api_key=API_KEY, city=city, lat=lat, lon=lon, units=units)
    except WeatherServiceError as exc:
        logger.warning("weather lookup failed: %s", exc)
        return jsonify({"error": str(exc)}), exc.status_code

    if DB_AVAILABLE:
        try:
            db.record_search(
                data["location"]["name"],
                data["location"]["country"],
                data["location"]["lat"],
                data["location"]["lon"],
            )
        except Exception:
            logger.exception("Failed to record search history; continuing anyway.")
    return jsonify(data)


@app.route("/api/history", methods=["GET"])
def api_history_get():
    if not DB_AVAILABLE:
        return jsonify([])
    return jsonify(db.recent_searches())


@app.route("/api/history", methods=["DELETE"])
def api_history_clear():
    if DB_AVAILABLE:
        db.clear_history()
    return jsonify({"ok": True})


@app.route("/api/pinned", methods=["GET"])
def api_pinned_list():
    if not DB_AVAILABLE:
        return jsonify([])

    units = request.args.get("units", "metric")
    pins = db.list_pinned()
    if not pins:
        return jsonify([])

    # Each pinned city is an independent lookup, so fetch all of them at
    # once instead of one-by-one — the same pattern weather_service uses
    # internally for forecast + air quality, applied across cities here.
    def lookup(pin):
        try:
            data = get_weather(api_key=API_KEY, lat=pin["lat"], lon=pin["lon"], units=units)
            return {
                "city": pin["city"], "country": pin["country"],
                "temp": data["current"]["temp"], "icon": data["current"]["icon"],
                "sky_theme": data["sky_theme"], "ok": True,
            }
        except WeatherServiceError:
            return {"city": pin["city"], "country": pin["country"], "ok": False}

    with ThreadPoolExecutor(max_workers=min(6, len(pins))) as pool:
        results = list(pool.map(lookup, pins))
    return jsonify(results)


@app.route("/api/pinned", methods=["POST"])
def api_pinned_add():
    if not DB_AVAILABLE:
        return jsonify({"error": "Pinning isn't available right now."}), 503
    payload = request.get_json(silent=True) or {}
    city, country = payload.get("city"), payload.get("country")
    lat, lon = payload.get("lat"), payload.get("lon")
    if not city or not country or lat is None or lon is None:
        return jsonify({"error": "city, country, lat and lon are required"}), 400
    if len(db.list_pinned(limit=999)) >= 6:
        return jsonify({"error": "You can pin up to 6 cities — unpin one first."}), 400
    db.pin_city(city, country, float(lat), float(lon))
    return jsonify({"ok": True})


@app.route("/api/pinned", methods=["DELETE"])
def api_pinned_remove():
    if not DB_AVAILABLE:
        return jsonify({"ok": True})
    payload = request.get_json(silent=True) or {}
    db.unpin_city(payload.get("city", ""), payload.get("country", ""))
    return jsonify({"ok": True})


@app.errorhandler(404)
def not_found(_exc):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(_exc):
    logger.exception("Unhandled server error")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    if not API_KEY:
        logger.warning(
            "OPENWEATHER_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    app.run(debug=True, port=5000)
