"""Unit tests for services.weather_service and services.cache.

Run with:  pytest -v

External HTTP calls are mocked so the suite runs instantly and doesn't
need a real API key or network access.
"""

import time
from unittest.mock import patch, MagicMock

import pytest

from services.cache import TTLCache
from services.exceptions import CityNotFoundError, InvalidAPIKeyError, WeatherServiceError
from services.weather_service import deg_to_compass, get_weather, _sun_progress, classify_sky, advisory
from services import weather_service


@pytest.fixture(autouse=True)
def clear_module_cache():
    """The module-level cache in weather_service persists across tests
    since it's created once at import time — clear it before each test
    so a cache hit in one test can't mask a bug (or a fresh code path)
    in another."""
    weather_service._cache.clear()
    yield
    weather_service._cache.clear()


# ---------- pure logic ----------

@pytest.mark.parametrize("deg,expected", [
    (0, "N"),
    (90, "E"),
    (180, "S"),
    (270, "W"),
    (359, "N"),
    (23, "NNE"),
])
def test_deg_to_compass(deg, expected):
    assert deg_to_compass(deg) == expected


def test_sun_progress_shape():
    now = int(time.time())
    result = _sun_progress(now - 3600, now + 3600, tz_offset_seconds=0)
    assert 0.0 <= result["day_progress"] <= 1.0
    assert result["is_daytime"] is True
    assert "sunrise" in result and "sunset" in result


def test_sun_progress_before_sunrise():
    now = int(time.time())
    result = _sun_progress(now + 3600, now + 7200, tz_offset_seconds=0)
    assert result["is_daytime"] is False
    assert result["day_progress"] == 0.0


@pytest.mark.parametrize("weather_id,is_daytime,expected", [
    (800, True, "clear_day"),
    (800, False, "clear_night"),
    (801, True, "cloudy_day"),
    (802, False, "cloudy_night"),
    (211, True, "storm"),
    (301, True, "drizzle"),
    (501, True, "rain"),
    (601, True, "snow"),
    (741, True, "mist"),
])
def test_classify_sky(weather_id, is_daytime, expected):
    assert classify_sky(weather_id, is_daytime) == expected


def test_advisory_rain_takes_priority():
    msg = advisory(weather_id=500, temp=25, wind_speed=2, aqi=1, units="metric")
    assert "umbrella" in msg.lower()


def test_advisory_storm_takes_priority_over_rain_group():
    msg = advisory(weather_id=211, temp=25, wind_speed=2, aqi=1, units="metric")
    assert "storm" in msg.lower() or "indoors" in msg.lower()


def test_advisory_poor_air_quality():
    msg = advisory(weather_id=800, temp=25, wind_speed=2, aqi=5, units="metric")
    assert "air quality" in msg.lower()


def test_advisory_pleasant_default():
    msg = advisory(weather_id=800, temp=22, wind_speed=2, aqi=1, units="metric")
    assert "pleasant" in msg.lower()


def test_advisory_hot_metric_vs_imperial_thresholds():
    hot_metric = advisory(weather_id=800, temp=35, wind_speed=2, aqi=1, units="metric")
    hot_imperial = advisory(weather_id=800, temp=95, wind_speed=2, aqi=1, units="imperial")
    assert "hot" in hot_metric.lower()
    assert "hot" in hot_imperial.lower()


# ---------- cache ----------

def test_cache_set_and_get():
    cache = TTLCache(ttl_seconds=60)
    cache.set("key", {"a": 1})
    assert cache.get("key") == {"a": 1}


def test_cache_expiry():
    cache = TTLCache(ttl_seconds=0)  # expires immediately
    cache.set("key", "value")
    time.sleep(0.01)
    assert cache.get("key") is None


def test_cache_miss_returns_none():
    cache = TTLCache(ttl_seconds=60)
    assert cache.get("missing") is None


# ---------- weather_service.get_weather, HTTP mocked ----------

def _mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.json.return_value = json_data or {}
    return resp


CURRENT_JSON = {
    "coord": {"lat": 19.07, "lon": 72.87},
    "name": "Mumbai",
    "sys": {"country": "IN", "sunrise": 0, "sunset": 100000},
    "timezone": 19800,
    "weather": [{"description": "clear sky", "icon": "01d", "id": 800}],
    "main": {"temp": 30, "feels_like": 33, "humidity": 70, "pressure": 1008},
    "clouds": {"all": 10},
    "wind": {"speed": 3.1, "deg": 200},
    "visibility": 8000,
}
FORECAST_JSON = {"list": [
    {"dt": 1, "dt_txt": "2026-08-05 12:00:00", "main": {"temp": 30, "temp_max": 31, "temp_min": 27},
     "weather": [{"description": "clear sky", "icon": "01d"}]},
]}
AQI_JSON = {"list": [{"main": {"aqi": 2}, "components": {"pm2_5": 12.3, "pm10": 20.1}}]}


@patch("services.weather_service.requests.get")
def test_get_weather_success(mock_get):
    def side_effect(url, params, timeout):
        if "air_pollution" in url:
            return _mock_response(json_data=AQI_JSON)
        if "forecast" in url:
            return _mock_response(json_data=FORECAST_JSON)
        return _mock_response(json_data=CURRENT_JSON)

    mock_get.side_effect = side_effect
    result = get_weather(api_key="fake-key", city="Mumbai", units="metric")

    assert result["location"]["name"] == "Mumbai"
    assert result["current"]["temp"] == 30
    assert result["air_quality"]["category"] == "Fair"
    assert len(result["forecast"]) == 1
    assert len(result["hourly"]) == 1
    assert isinstance(result["advisory"], str) and len(result["advisory"]) > 0
    assert result["cached"] is False


@patch("services.weather_service.requests.get")
def test_get_weather_city_not_found(mock_get):
    mock_get.return_value = _mock_response(status_code=404)
    with pytest.raises(CityNotFoundError):
        get_weather(api_key="fake-key", city="Nowhereville", units="metric")


@patch("services.weather_service.requests.get")
def test_get_weather_bad_api_key(mock_get):
    mock_get.return_value = _mock_response(status_code=401)
    with pytest.raises(InvalidAPIKeyError):
        get_weather(api_key="wrong-key", city="Mumbai", units="metric")


def test_get_weather_requires_key():
    with pytest.raises(InvalidAPIKeyError):
        get_weather(api_key="", city="Mumbai")


@patch("services.weather_service.requests.get")
def test_get_weather_by_zip_code(mock_get):
    def side_effect(url, params, timeout):
        if "air_pollution" in url:
            return _mock_response(json_data=AQI_JSON)
        if "forecast" in url:
            return _mock_response(json_data=FORECAST_JSON)
        # confirm the zip param was actually sent, not q=
        assert params.get("zip") == "400001,IN"
        assert "q" not in params
        return _mock_response(json_data=CURRENT_JSON)

    mock_get.side_effect = side_effect
    result = get_weather(api_key="fake-key", zip_code="400001,IN", units="metric")
    assert result["location"]["name"] == "Mumbai"


def test_get_weather_requires_city_zip_or_coords():
    with pytest.raises(WeatherServiceError):
        get_weather(api_key="fake-key")
