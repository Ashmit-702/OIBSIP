"""tests/test_api.py — end-to-end API tests via the Flask test client."""

import json

import pytest


class TestOnboarding:
    def test_onboarding_creates_profile_and_redirects(self, client):
        response = client.post("/onboarding", data={
            "username": "Jamie", "height_m": "1.68", "age": "25", "sex": "female",
            "activity_level": "light", "goal_type": "maintain",
        })
        assert response.status_code == 302
        assert "/dashboard" in response.headers["Location"]

    def test_onboarding_rejects_invalid_height(self, client):
        response = client.post("/onboarding", data={
            "username": "Jamie", "height_m": "not-a-number",
            "activity_level": "light", "goal_type": "maintain",
        })
        assert response.status_code == 400

    def test_onboarding_rejects_missing_username(self, client):
        response = client.post("/onboarding", data={
            "height_m": "1.68", "activity_level": "light", "goal_type": "maintain",
        })
        assert response.status_code == 400

    def test_dashboard_redirects_without_profile(self, client):
        response = client.get("/dashboard")
        assert response.status_code == 302
        assert "/onboarding" in response.headers["Location"]


class TestHealthAPI:
    def test_create_record_requires_profile(self, client):
        response = client.post("/api/health", json={"weight_kg": 70})
        assert response.status_code == 400

    def test_create_record_success(self, onboarded_client):
        response = onboarded_client.post("/api/health", json={
            "weight_kg": 75.0, "entry_date": "2026-01-10", "water_l": 2.0, "steps": 8000, "sleep_hours": 7.5,
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["record"]["weight_kg"] == 75.0
        # BMI should be computed server-side from weight/height, matching weight/height^2.
        expected_bmi = round(75.0 / (1.75 ** 2), 2)
        assert data["record"]["bmi"] == expected_bmi
        assert data["record"]["category"] in ("Underweight", "Normal", "Overweight", "Obese")

    def test_create_record_rejects_invalid_weight(self, onboarded_client):
        response = onboarded_client.post("/api/health", json={"weight_kg": -5})
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_create_record_rejects_future_date(self, onboarded_client):
        response = onboarded_client.post("/api/health", json={
            "weight_kg": 75.0, "entry_date": "2099-01-01",
        })
        assert response.status_code == 400

    def test_update_and_delete_record(self, onboarded_client):
        created = onboarded_client.post("/api/health", json={"weight_kg": 75.0, "entry_date": "2026-01-10"})
        record_id = created.get_json()["record"]["id"]

        updated = onboarded_client.put(f"/api/health/{record_id}", json={"weight_kg": 74.0})
        assert updated.status_code == 200
        assert updated.get_json()["record"]["weight_kg"] == 74.0

        deleted = onboarded_client.delete(f"/api/health/{record_id}")
        assert deleted.status_code == 200

        missing = onboarded_client.put(f"/api/health/{record_id}", json={"weight_kg": 73.0})
        assert missing.status_code == 404

    def test_history_endpoint_returns_records(self, onboarded_client):
        onboarded_client.post("/api/health", json={"weight_kg": 75.0, "entry_date": "2026-01-10"})
        response = onboarded_client.get("/api/health/history")
        assert response.status_code == 200
        assert response.get_json()["count"] == 1


class TestDashboardAPI:
    def test_dashboard_without_records_shows_empty_state(self, onboarded_client):
        response = onboarded_client.get("/api/dashboard")
        assert response.status_code == 200
        assert response.get_json()["has_data"] is False

    def test_dashboard_with_records_computes_bmi_correctly(self, onboarded_client):
        onboarded_client.post("/api/health", json={"weight_kg": 75.0, "entry_date": "2026-01-10"})
        response = onboarded_client.get("/api/dashboard")
        data = response.get_json()
        assert data["has_data"] is True
        expected_bmi = round(75.0 / (1.75 ** 2), 2)
        assert data["bmi"] == expected_bmi


class TestGoalsAPI:
    def test_set_and_get_goal(self, onboarded_client):
        response = onboarded_client.post("/api/goals", json={
            "goal_type": "lose", "target_weight_kg": 68.0, "target_date": "2026-06-01",
        })
        assert response.status_code == 200
        assert response.get_json()["goal"]["target_weight_kg"] == 68.0

        fetched = onboarded_client.get("/api/goals")
        assert fetched.get_json()["goal"]["goal_type"] == "lose"

    def test_invalid_goal_type_rejected(self, onboarded_client):
        response = onboarded_client.post("/api/goals", json={
            "goal_type": "not_a_type", "target_weight_kg": 68.0,
        })
        assert response.status_code == 400


class TestReportsAPI:
    def test_report_requires_data(self, onboarded_client):
        response = onboarded_client.get("/api/report")
        assert response.status_code == 404

    def test_report_generates_pdf(self, onboarded_client):
        onboarded_client.post("/api/health", json={"weight_kg": 75.0, "entry_date": "2026-01-10"})
        response = onboarded_client.get("/api/report")
        assert response.status_code == 200
        assert response.mimetype == "application/pdf"
        assert response.data[:4] == b"%PDF"

    def test_csv_export(self, onboarded_client):
        onboarded_client.post("/api/health", json={"weight_kg": 75.0, "entry_date": "2026-01-10"})
        response = onboarded_client.get("/api/export")
        assert response.status_code == 200
        assert b"Date" in response.data
        assert b"75.0" in response.data


class TestSecurityHeaders:
    def test_security_headers_present(self, client):
        response = client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
