"""tests/test_goal_service.py — goal progress, pace, and ETA calculations."""

from datetime import date, timedelta

import pytest

from app.services import goal_service


def make_records(weight_dates):
    return [
        {"entry_date": d, "weight_kg": w, "bmi": 24.0, "category": "Normal"}
        for d, w in weight_dates
    ]


class TestGoalProgress:
    def test_no_records_returns_none(self):
        assert goal_service.compute_goal_progress([], 70.0) is None

    def test_zero_percent_at_start(self):
        records = make_records([("2026-01-01", 80.0)])
        progress = goal_service.compute_goal_progress(records, 70.0)
        assert progress["percent"] == 0

    def test_partial_progress(self):
        records = make_records([("2026-01-01", 80.0), ("2026-01-15", 75.0)])
        progress = goal_service.compute_goal_progress(records, 70.0)
        assert progress["percent"] == 50

    def test_full_progress_capped_at_100(self):
        records = make_records([("2026-01-01", 80.0), ("2026-01-15", 65.0)])
        progress = goal_service.compute_goal_progress(records, 70.0)
        assert progress["percent"] == 100

    def test_overshooting_does_not_exceed_100(self):
        records = make_records([("2026-01-01", 80.0), ("2026-01-15", 50.0)])
        progress = goal_service.compute_goal_progress(records, 70.0)
        assert progress["percent"] == 100

    def test_no_change_needed_is_100_percent(self):
        records = make_records([("2026-01-01", 70.0)])
        progress = goal_service.compute_goal_progress(records, 70.0)
        assert progress["percent"] == 100


class TestRequiredPace:
    def test_no_target_date_returns_none(self):
        records = make_records([("2026-01-01", 80.0)])
        assert goal_service.compute_required_pace(records, 70.0, None) is None

    def test_past_target_date_marked_infeasible(self):
        records = make_records([("2026-01-01", 80.0)])
        past_date = (date.today() - timedelta(days=5)).isoformat()
        pace = goal_service.compute_required_pace(records, 70.0, past_date)
        assert pace["feasible"] is False

    def test_reasonable_pace_marked_feasible(self):
        records = make_records([("2026-01-01", 80.0)])
        future_date = (date.today() + timedelta(days=120)).isoformat()
        pace = goal_service.compute_required_pace(records, 75.0, future_date)
        assert pace["feasible"] is True

    def test_unreasonable_pace_marked_infeasible(self):
        records = make_records([("2026-01-01", 90.0)])
        future_date = (date.today() + timedelta(days=7)).isoformat()
        pace = goal_service.compute_required_pace(records, 60.0, future_date)
        assert pace["feasible"] is False


class TestEstimateCompletion:
    def test_insufficient_data_not_available(self):
        records = make_records([("2026-01-01", 80.0)])
        result = goal_service.estimate_completion(records, 70.0)
        assert result["available"] is False

    def test_available_with_enough_trend_data(self):
        records = make_records([
            ("2026-01-01", 82.0), ("2026-01-08", 81.0), ("2026-01-15", 80.0), ("2026-01-22", 79.0),
        ])
        result = goal_service.estimate_completion(records, 70.0)
        assert result["available"] is True
        assert result["eta_date"] is not None


class TestBuildGoalSummary:
    def test_summary_combines_all_parts(self):
        records = make_records([
            ("2026-01-01", 82.0), ("2026-01-08", 81.0), ("2026-01-15", 80.0),
        ])
        goal = {"goal_type": "lose", "target_weight_kg": 75.0, "target_date": None}
        summary = goal_service.build_goal_summary(records, goal)
        assert summary["goal_type"] == "lose"
        assert summary["progress"] is not None
        assert "estimated_completion" in summary
