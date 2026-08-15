"""Weather service: talks to OpenWeatherMap and shapes the response
for the frontend.

Design notes (useful context if you're explaining this in an interview):
- The three upstream calls (current weather, forecast, air quality) are
  independent once we have coordinates, so the forecast + air-quality
  calls run concurrently via a ThreadPoolExecutor to cut latency roughly
  in half versus calling them one after another.
- Results are cached for a few minutes per (lat, lon, units) to stay
  well under the free-tier rate limit and to make repeat searches feel
  instant.
- All upstream failures are translated into the custom exceptions in
  exceptions.py so the Flask route layer doesn't need to know anything
  about OpenWeatherMap's specific status codes.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import Any

import requests

from .cache import TTLCache
from .exceptions import (
    CityNotFoundError,
    InvalidAPIKeyError,
    UpstreamTimeoutError,
    WeatherServiceError,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openweathermap.org/data/2.5"
REQUEST_TIMEOUT = 6  # seconds

_cache = TTLCache(ttl_seconds=600)

AQI_LABELS = {
    1: "Good",
    2: "Fair",
    3: "Moderate",
    4: "Poor",
    5: "Very Poor",
}

_COMPASS_POINTS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def deg_to_compass(deg: float) -> str:
    """Convert a wind direction in degrees to a 16-point compass label."""
    idx = round(deg / 22.5) % 16
    return _COMPASS_POINTS[idx]


def _get(url: str, params: dict) -> dict:
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    except requests.Timeout as exc:
        raise UpstreamTimeoutError("The weather service took too long to respond.") from exc
    except requests.RequestException as exc:
        raise WeatherServiceError(f"Network error contacting the weather service: {exc}") from exc

    if resp.status_code == 401:
        raise InvalidAPIKeyError("The OpenWeatherMap API key was rejected.")
    if resp.status_code == 404:
        raise CityNotFoundError("Couldn't find that place.")
    if not resp.ok:
        raise WeatherServiceError(f"Weather service returned status {resp.status_code}.")
    return resp.json()


def _fetch_current(lat: float | None, lon: float | None, city: str | None,
                    zip_code: str | None, units: str, api_key: str) -> dict:
    params = {"units": units, "appid": api_key}
    if city:
        params["q"] = city
    elif zip_code:
        params["zip"] = zip_code
    else:
        params["lat"] = lat
        params["lon"] = lon
    return _get(f"{BASE_URL}/weather", params)


def _fetch_forecast(lat: float, lon: float, units: str, api_key: str) -> dict:
    params = {"lat": lat, "lon": lon, "units": units, "appid": api_key}
    return _get(f"{BASE_URL}/forecast", params)


def _fetch_air_quality(lat: float, lon: float, api_key: str) -> dict:
    params = {"lat": lat, "lon": lon, "appid": api_key}
    return _get(f"{BASE_URL}/air_pollution", params)


def _sun_progress(sunrise_ts: int, sunset_ts: int, tz_offset_seconds: int) -> dict:
    """Work out how far through daylight we are, as a 0-1 fraction, plus
    human-readable local sunrise/sunset times. Done in Python so the
    frontend just draws a percentage instead of re-deriving timezones."""
    now_utc = datetime.now(timezone.utc)
    tz = timezone(timedelta(seconds=tz_offset_seconds))
    now_local = now_utc.astimezone(tz)
    sunrise_local = datetime.fromtimestamp(sunrise_ts, tz=timezone.utc).astimezone(tz)
    sunset_local = datetime.fromtimestamp(sunset_ts, tz=timezone.utc).astimezone(tz)

    day_length = (sunset_local - sunrise_local).total_seconds()
    elapsed = (now_local - sunrise_local).total_seconds()
    is_daytime = 0 <= elapsed <= day_length
    progress = min(1.0, max(0.0, elapsed / day_length)) if day_length > 0 else 0.0

    return {
        "sunrise": sunrise_local.strftime("%H:%M"),
        "sunset": sunset_local.strftime("%H:%M"),
        "local_time": now_local.strftime("%H:%M"),
        "day_progress": round(progress, 4),
        "is_daytime": is_daytime,
    }


def classify_sky(weather_id: int, is_daytime: bool) -> str:
    """Map OpenWeatherMap's condition-code taxonomy to one of a small set
    of "sky themes" the frontend uses to pick a background treatment.

    OWM group codes: 2xx thunderstorm, 3xx drizzle, 5xx rain, 6xx snow,
    7xx atmosphere (mist/haze/fog/etc), 800 clear, 80x clouds.
    """
    group = weather_id // 100
    if group == 2:
        return "storm"
    if group == 3:
        return "drizzle"
    if group == 5:
        return "rain"
    if group == 6:
        return "snow"
    if group == 7:
        return "mist"
    if weather_id == 800:
        return "clear_day" if is_daytime else "clear_night"
    if group == 8:
        return "cloudy_day" if is_daytime else "cloudy_night"
    return "clear_day" if is_daytime else "clear_night"


def _hourly_forecast(forecast_json: dict, count: int = 8) -> list[dict]:
    """Next `count` 3-hour forecast slots, for an hourly-look strip."""
    hours = []
    for entry in forecast_json.get("list", [])[:count]:
        time_str = entry["dt_txt"].split(" ")[1][:5]
        hours.append({
            "time": time_str,
            "icon": entry["weather"][0]["icon"],
            "temp": round(entry["main"]["temp"]),
            "pop": round(entry.get("pop", 0) * 100),  # probability of precipitation, %
        })
    return hours


def advisory(*, weather_id: int, temp: float, wind_speed: float, aqi: int, units: str) -> str:
    """A short, rule-based "what should I do" line. Deliberately simple
    (no ML, no external call) — the point is showing clean decision logic
    over structured data, which is exactly what a lot of real backend
    work looks like."""
    group = weather_id // 100
    wind_threshold = 10.8 if units == "metric" else 24  # ~ Beaufort force 6

    if group == 2:
        return "Thunderstorms nearby — best to stay indoors if you can."
    if group in (3, 5):
        return "Rain expected — grab an umbrella before heading out."
    if group == 6:
        return "Snow expected — watch for slippery roads and sidewalks."
    if group == 7:
        return "Reduced visibility outside — take it slow if you're driving."
    if aqi >= 4:
        return "Air quality is poor today — consider a mask if you're sensitive to pollution."
    if wind_speed >= wind_threshold:
        return "Quite windy out there — secure loose items if you're outside."
    hot_threshold = 33 if units == "metric" else 91
    cold_threshold = 5 if units == "metric" else 41
    if temp >= hot_threshold:
        return "Hot out there — stay hydrated and avoid peak sun hours."
    if temp <= cold_threshold:
        return "Chilly today — a jacket is a good idea."
    return "Conditions look pleasant — a good day to be outside."


def _daily_forecast(forecast_json: dict) -> list[dict]:
    """Reduce the 3-hour forecast feed to one representative entry per day,
    preferring the reading closest to local noon."""
    by_date: dict[str, dict] = {}
    for entry in forecast_json.get("list", []):
        date_str, time_str = entry["dt_txt"].split(" ")
        if date_str not in by_date or time_str == "12:00:00":
            by_date[date_str] = entry

    days = []
    for date_str, entry in list(by_date.items())[:5]:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        days.append({
            "date": date_str,
            "day_label": dt.strftime("%a"),
            "icon": entry["weather"][0]["icon"],
            "description": entry["weather"][0]["description"],
            "temp_max": round(entry["main"]["temp_max"]),
            "temp_min": round(entry["main"]["temp_min"]),
        })
    return days


def get_weather(*, api_key: str, city: str | None = None, zip_code: str | None = None,
                 lat: float | None = None, lon: float | None = None,
                 units: str = "metric") -> dict:
    """Main entry point used by the Flask route.

    Pass exactly one of: `city`, `zip_code`, or (`lat`, `lon`). Returns a
    plain dict ready to be jsonify()'d.
    """
    if not api_key:
        raise InvalidAPIKeyError("No OpenWeatherMap API key is configured on the server.")
    if not city and not zip_code and (lat is None or lon is None):
        raise WeatherServiceError("Provide a city name, a ZIP/postal code, or lat/lon coordinates.")

    cache_key = f"{city or zip_code or f'{lat:.3f},{lon:.3f}'}|{units}"
    cached = _cache.get(cache_key)
    if cached is not None:
        logger.info("cache hit for %s", cache_key)
        return {**cached, "cached": True}

    start = time.monotonic()

    current = _fetch_current(lat, lon, city, zip_code, units, api_key)
    resolved_lat = current["coord"]["lat"]
    resolved_lon = current["coord"]["lon"]

    # Forecast and air-quality are independent calls once we have
    # coordinates — fetch them concurrently to cut wall-clock latency.
    with ThreadPoolExecutor(max_workers=2) as pool:
        forecast_future = pool.submit(_fetch_forecast, resolved_lat, resolved_lon, units, api_key)
        aqi_future = pool.submit(_fetch_air_quality, resolved_lat, resolved_lon, api_key)
        forecast_json = forecast_future.result()
        aqi_json = aqi_future.result()

    elapsed_ms = round((time.monotonic() - start) * 1000)
    logger.info("fetched weather for %s in %d ms", city or (resolved_lat, resolved_lon), elapsed_ms)

    wind_deg = current["wind"].get("deg", 0)
    aqi_index = aqi_json["list"][0]["main"]["aqi"]
    sun = _sun_progress(
        current["sys"]["sunrise"],
        current["sys"]["sunset"],
        current["timezone"],
    )
    sky_theme = classify_sky(current["weather"][0]["id"], sun["is_daytime"])

    result = {
        "location": {
            "name": current["name"],
            "country": current["sys"]["country"],
            "lat": resolved_lat,
            "lon": resolved_lon,
        },
        "current": {
            "temp": round(current["main"]["temp"]),
            "feels_like": round(current["main"]["feels_like"]),
            "description": current["weather"][0]["description"],
            "icon": current["weather"][0]["icon"],
            "humidity": current["main"]["humidity"],
            "pressure": current["main"]["pressure"],
            "visibility_km": round(current.get("visibility", 0) / 1000, 1),
            "clouds_pct": current["clouds"]["all"],
            "wind_speed": current["wind"]["speed"],
            "wind_deg": wind_deg,
            "wind_compass": deg_to_compass(wind_deg),
        },
        "sun": sun,
        "sky_theme": sky_theme,
        "air_quality": {
            "aqi": aqi_index,
            "category": AQI_LABELS.get(aqi_index, "Unknown"),
            "pm2_5": round(aqi_json["list"][0]["components"].get("pm2_5", 0), 1),
            "pm10": round(aqi_json["list"][0]["components"].get("pm10", 0), 1),
        },
        "forecast": _daily_forecast(forecast_json),
        "hourly": _hourly_forecast(forecast_json),
        "trend": [round(e["main"]["temp"]) for e in forecast_json.get("list", [])[:16]],
        "advisory": advisory(
            weather_id=current["weather"][0]["id"],
            temp=current["main"]["temp"],
            wind_speed=current["wind"]["speed"],
            aqi=aqi_index,
            units=units,
        ),
        "units": units,
        "fetched_in_ms": elapsed_ms,
        "cached": False,
    }

    _cache.set(cache_key, result)
    return result
