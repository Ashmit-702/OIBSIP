"""Integration-style tests for the Flask routes, using Flask's test
client (no real server, no real network — weather lookups are mocked)."""

import importlib
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    # Point the DB at a throwaway file for this test run so tests don't
    # pollute (or depend on) a real station.db.
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key")

    import services.db as db_module
    db_module.DB_PATH = tmp_path / "test_station.db"

    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_index_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_weather_requires_city_or_coords(client):
    resp = client.get("/api/weather")
    assert resp.status_code == 400


def test_weather_rejects_bad_units(client):
    resp = client.get("/api/weather?city=Mumbai&units=kelvin")
    assert resp.status_code == 400


def test_history_starts_empty(client):
    resp = client.get("/api/history")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_pinned_starts_empty(client):
    resp = client.get("/api/pinned")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_pin_then_list_then_unpin(client):
    payload = {"city": "Mumbai", "country": "IN", "lat": 19.07, "lon": 72.87}

    add = client.post("/api/pinned", json=payload)
    assert add.status_code == 200

    with patch("app.get_weather") as mock_weather:
        mock_weather.return_value = {
            "current": {"temp": 30, "icon": "01d"},
            "sky_theme": "clear_day",
        }
        listed = client.get("/api/pinned")
    assert listed.status_code == 200
    body = listed.get_json()
    assert len(body) == 1
    assert body[0]["city"] == "Mumbai"
    assert body[0]["ok"] is True
    assert body[0]["temp"] == 30

    remove = client.delete("/api/pinned", json={"city": "Mumbai", "country": "IN"})
    assert remove.status_code == 200
    after = client.get("/api/pinned")
    assert after.get_json() == []


def test_pin_requires_all_fields(client):
    resp = client.post("/api/pinned", json={"city": "Mumbai"})
    assert resp.status_code == 400


def test_pin_cap_at_six(client):
    for i in range(6):
        client.post("/api/pinned", json={"city": f"City{i}", "country": "IN", "lat": i, "lon": i})
    resp = client.post("/api/pinned", json={"city": "OneTooMany", "country": "IN", "lat": 1, "lon": 1})
    assert resp.status_code == 400
