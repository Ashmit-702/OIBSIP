"""tests/test_analytics_service.py — trend statistics and forecasting."""

from datetime import date, timedelta

import pytest

from app.services import analytics_service


def make_records(weight_dates_bmis):
    """[(date_str, weight, bmi), ...] -> list of dict records like the DB returns."""
    return [
        {"entry_date": d, "weight_kg": w, "bmi": b, "category": "Normal",
         "water_l": None, "steps": None, "sleep_hours": None}
        for d, w, b in weight_dates_bmis
    ]


class TestWeightHistoryStats:
    def test_empty_records(self):
        stats = analytics_service.weight_history_stats([])
        assert stats["has_data"] is False

    def test_single_record(self):
        records = make_records([("2026-01-01", 80.0, 26.1)])
        stats = analytics_service.weight_history_stats(records)
        assert stats["has_data"] is True
        assert stats["current_weight"] == 80.0
        assert stats["starting_weight"] == 80.0
        assert stats["total_change"] == 0

    def test_weight_loss_trend(self):
        records = make_records([
            ("2026-01-01", 80.0, 26.1), ("2026-01-08", 79.0, 25.8), ("2026-01-15", 78.0, 25.5),
        ])
        stats = analytics_service.weight_history_stats(records)
        assert stats["total_change"] == -2.0
        assert stats["highest_weight"] == 80.0
        assert stats["lowest_weight"] == 78.0
        assert stats["average_weight"] == pytest.approx(79.0, abs=0.1)
        assert stats["weekly_rate"] < 0


class TestFilterByWindow:
    def test_all_returns_everything(self):
        records = make_records([("2020-01-01", 80.0, 26.1)])
        assert analytics_service.filter_by_window(records, "All") == records

    def test_7d_excludes_old_entries(self):
        old_date = (date.today() - timedelta(days=30)).isoformat()
        recent_date = (date.today() - timedelta(days=2)).isoformat()
        records = make_records([(old_date, 80.0, 26.1), (recent_date, 78.0, 25.5)])
        filtered = analytics_service.filter_by_window(records, "7D")
        assert len(filtered) == 1
        assert filtered[0]["entry_date"] == recent_date


class TestLoggingConsistency:
    def test_no_records(self):
        result = analytics_service.compute_logging_consistency([])
        assert result["percent"] == 0

    def test_full_month_logged(self):
        records = make_records([
            ((date.today() - timedelta(days=i)).isoformat(), 80.0, 26.1) for i in range(30)
        ])
        result = analytics_service.compute_logging_consistency(records, window_days=30)
        assert result["percent"] == 100

    def test_partial_logging(self):
        records = make_records([
            ((date.today() - timedelta(days=i)).isoformat(), 80.0, 26.1) for i in range(0, 30, 2)
        ])
        result = analytics_service.compute_logging_consistency(records, window_days=30)
        assert 0 < result["percent"] < 100


class TestStreak:
    def test_no_records(self):
        assert analytics_service.compute_streak([]) == 0

    def test_consecutive_days(self):
        records = make_records([
            ((date.today() - timedelta(days=i)).isoformat(), 80.0, 26.1) for i in range(5)
        ])
        assert analytics_service.compute_streak(records) == 5

    def test_broken_streak(self):
        records = make_records([
            ("2026-01-01", 80.0, 26.1), ("2026-01-02", 79.9, 26.0),
            ("2026-01-10", 79.0, 25.8), ("2026-01-11", 78.9, 25.7), ("2026-01-12", 78.8, 25.6),
        ])
        assert analytics_service.compute_streak(records) == 3


class TestForecastTrend:
    def test_insufficient_data(self):
        records = make_records([("2026-01-01", 80.0, 26.1)])
        result = analytics_service.forecast_trend(records)
        assert result["available"] is False

    def test_same_day_entries_insufficient(self):
        records = make_records([("2026-01-01", 80.0, 26.1), ("2026-01-01", 79.5, 25.9)])
        result = analytics_service.forecast_trend(records)
        assert result["available"] is False

    def test_falling_trend_detected(self):
        records = make_records([
            ("2026-01-01", 82.0, 26.8), ("2026-01-08", 81.0, 26.5),
            ("2026-01-15", 80.0, 26.1), ("2026-01-22", 79.0, 25.8),
        ])
        result = analytics_service.forecast_trend(records)
        assert result["available"] is True
        assert result["trend_direction"] == "falling"
        assert result["weight_change_per_week"] < 0

    def test_goal_eta_computed_when_moving_toward_goal(self):
        records = make_records([
            ("2026-01-01", 82.0, 26.8), ("2026-01-08", 81.0, 26.5),
            ("2026-01-15", 80.0, 26.1), ("2026-01-22", 79.0, 25.8),
        ])
        result = analytics_service.forecast_trend(records, goal_weight_kg=75.0)
        assert result["goal_eta_days"] is not None
        assert result["goal_eta_days"] > 0

    def test_goal_eta_none_when_moving_away_from_goal(self):
        records = make_records([
            ("2026-01-01", 78.0, 25.5), ("2026-01-08", 79.0, 25.8),
            ("2026-01-15", 80.0, 26.1), ("2026-01-22", 81.0, 26.5),
        ])
        result = analytics_service.forecast_trend(records, goal_weight_kg=75.0)
        assert result["goal_eta_days"] is None
