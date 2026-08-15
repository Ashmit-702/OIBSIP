"""tests/test_insight_and_score.py — deterministic insight generation and the wellness score."""

from datetime import date, timedelta

import pytest

from app.services import insight_service, score_service


def make_records(days_ago_weights, water=None, steps=None, sleep=None):
    records = []
    for days_ago, weight in days_ago_weights:
        d = (date.today() - timedelta(days=days_ago)).isoformat()
        records.append({
            "entry_date": d, "weight_kg": weight, "bmi": round(weight / (1.75 ** 2), 2),
            "category": "Normal", "water_l": water, "steps": steps, "sleep_hours": sleep,
        })
    return records


class TestInsightService:
    def test_no_records_returns_empty(self):
        assert insight_service.generate_insights([]) == []

    def test_weight_decrease_detected(self):
        records = make_records([(29, 82.0), (1, 80.0)])
        insights = insight_service.generate_insights(records)
        assert any("decreased" in i for i in insights)

    def test_weight_increase_detected(self):
        records = make_records([(29, 78.0), (1, 80.0)])
        insights = insight_service.generate_insights(records)
        assert any("increased" in i for i in insights)

    def test_logging_consistency_mentioned(self):
        records = make_records([(i, 80.0) for i in range(10)])
        insights = insight_service.generate_insights(records)
        assert any("logged measurements" in i for i in insights)

    def test_insights_grounded_in_real_numbers(self):
        # Insight text should reflect the actual computed change, not a fixed string.
        records = make_records([(29, 90.0), (1, 80.0)])
        insights = insight_service.generate_insights(records)
        assert any("10" in i or "10.0" in i for i in insights)


class TestScoreService:
    def test_no_records_returns_none(self):
        assert score_service.compute_wellness_score([], {"available": False}) is None

    def test_score_within_bounds(self):
        records = make_records([(i, 80.0 - i * 0.05) for i in range(20)], water=2.0, steps=8000, sleep=7.5)
        forecast = {"available": True, "trend_direction": "falling"}
        result = score_service.compute_wellness_score(records, forecast, goal_type="lose")
        assert 0 <= result["score"] <= 100

    def test_components_sum_reasonably(self):
        records = make_records([(i, 80.0) for i in range(5)], water=2.0, steps=8000, sleep=7.5)
        forecast = {"available": False}
        result = score_service.compute_wellness_score(records, forecast)
        assert len(result["components"]) >= 3
        for c in result["components"]:
            assert 0 <= c["score"] <= c["max"]

    def test_missing_optional_data_excludes_component(self):
        records = make_records([(i, 80.0) for i in range(5)])  # no water/steps/sleep
        forecast = {"available": False}
        result = score_service.compute_wellness_score(records, forecast)
        labels = [c["label"] for c in result["components"]]
        assert "Hydration tracking" not in labels
        assert "Sleep tracking" not in labels
