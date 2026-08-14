"""
Test suite for bmi_logic.py — the core calculation, classification, streak/goal,
forecasting, and health-score logic. No network calls are made: get_ai_insights
is tested with GEMINI_API_KEY unset, which exercises the local fallback path
deterministically instead of hitting the real Gemini API.

Run with:  pytest tests/ -v
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

os.environ.pop("GEMINI_API_KEY", None)  # force the local fallback path for these tests

import bmi_logic


# --------------------------------------------------------------------------- #
# calculate_bmi
# --------------------------------------------------------------------------- #

def test_calculate_bmi_known_value():
    # 70kg / (1.75m)^2 = 22.857... -> 22.86
    assert bmi_logic.calculate_bmi(70, 1.75) == 22.86


def test_calculate_bmi_rejects_non_positive_weight():
    with pytest.raises(bmi_logic.ValidationError):
        bmi_logic.calculate_bmi(0, 1.75)
    with pytest.raises(bmi_logic.ValidationError):
        bmi_logic.calculate_bmi(-5, 1.75)


def test_calculate_bmi_rejects_non_positive_height():
    with pytest.raises(bmi_logic.ValidationError):
        bmi_logic.calculate_bmi(70, 0)


def test_calculate_bmi_rejects_height_in_cm_by_mistake():
    # A common user error: entering 175 instead of 1.75.
    with pytest.raises(bmi_logic.ValidationError):
        bmi_logic.calculate_bmi(70, 175)


# --------------------------------------------------------------------------- #
# classify_bmi
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("bmi,expected", [
    (17.9, "Underweight"),
    (18.5, "Normal"),
    (24.9, "Normal"),
    (25.0, "Overweight"),
    (29.9, "Overweight"),
    (30.0, "Obese"),
    (40.0, "Obese"),
])
def test_classify_bmi_boundaries(bmi, expected):
    assert bmi_logic.classify_bmi(bmi) == expected


# --------------------------------------------------------------------------- #
# ideal weight / BMR / calories / body fat / water
# --------------------------------------------------------------------------- #

def test_ideal_weight_range_scales_with_height():
    r = bmi_logic.calculate_ideal_weight_range(1.75)
    assert r["min"] < r["max"]
    assert r["min"] == round(18.5 * 1.75 ** 2, 1)
    assert r["max"] == round(24.9 * 1.75 ** 2, 1)


def test_bmr_male_vs_female_differ():
    male = bmi_logic.calculate_bmr(70, 1.75, 30, "male")
    female = bmi_logic.calculate_bmr(70, 1.75, 30, "female")
    # Mifflin-St Jeor adds +5 for men and -161 for women — a fixed 166 gap.
    assert male - female == 166


def test_daily_calories_scale_with_activity():
    bmr = 1600
    sedentary = bmi_logic.calculate_daily_calories(bmr, "sedentary")
    active = bmi_logic.calculate_daily_calories(bmr, "very_active")
    assert active > sedentary


def test_daily_calories_unknown_activity_defaults_to_sedentary():
    bmr = 1600
    assert bmi_logic.calculate_daily_calories(bmr, "not_a_real_level") == \
        bmi_logic.calculate_daily_calories(bmr, "sedentary")


def test_body_fat_never_negative():
    # Deliberately low inputs that could otherwise push the formula negative.
    result = bmi_logic.estimate_body_fat_percent(bmi=15, age=18, gender="male")
    assert result >= 0


def test_water_intake_scales_with_weight():
    assert bmi_logic.estimate_water_intake_liters(100) > bmi_logic.estimate_water_intake_liters(50)


# --------------------------------------------------------------------------- #
# Streak / achievements / goal progress
# --------------------------------------------------------------------------- #

def _entry(days_ago, weight=70.0, bmi=22.0):
    d = datetime.utcnow() - timedelta(days=days_ago)
    return {
        "created_at": d.strftime("%Y-%m-%d %H:%M:%S"),
        "weight_kg": weight,
        "bmi": bmi,
        "category": "Normal",
    }


def test_streak_counts_consecutive_days():
    history = [_entry(3), _entry(2), _entry(1), _entry(0)]
    assert bmi_logic.compute_streak(history) == 4


def test_streak_broken_by_gap():
    history = [_entry(5), _entry(1), _entry(0)]  # gap between day-5 and day-1
    assert bmi_logic.compute_streak(history) == 2


def test_streak_empty_history():
    assert bmi_logic.compute_streak([]) == 0


def test_goal_progress_toward_loss():
    history = [_entry(10, weight=80.0), _entry(0, weight=76.0)]
    progress = bmi_logic.compute_goal_progress(history, goal_weight_kg=70.0)
    assert progress["percent"] == 40  # (80-76)/(80-70) = 40%


def test_goal_progress_clips_to_100():
    history = [_entry(10, weight=80.0), _entry(0, weight=60.0)]  # overshot the goal
    progress = bmi_logic.compute_goal_progress(history, goal_weight_kg=70.0)
    assert progress["percent"] == 100


def test_goal_progress_none_without_history():
    assert bmi_logic.compute_goal_progress([], goal_weight_kg=70.0) is None


# --------------------------------------------------------------------------- #
# Hybrid AI Insight Engine (local fallback path — no network)
# --------------------------------------------------------------------------- #

def test_get_ai_insights_falls_back_locally_without_api_key():
    history = [_entry(1), _entry(0)]
    result = bmi_logic.get_ai_insights("Ash", 22.0, "Normal", history)
    assert result["available"] is True
    assert result["source"] == "local"
    assert "Ash" in result["message"]
    assert "22.0" in result["message"]


def test_get_ai_insights_never_leaks_key_or_raises():
    # Even with a garbage key set, get_ai_insights must never raise, and the
    # returned message must never contain the key itself.
    os.environ["GEMINI_API_KEY"] = "FAKE_KEY_SHOULD_NEVER_APPEAR_IN_OUTPUT"
    try:
        import importlib
        importlib.reload(bmi_logic)
        result = bmi_logic.get_ai_insights("Ash", 22.0, "Normal", [_entry(0)])
        assert "FAKE_KEY_SHOULD_NEVER_APPEAR_IN_OUTPUT" not in result["message"]
    finally:
        os.environ.pop("GEMINI_API_KEY", None)
        import importlib
        importlib.reload(bmi_logic)


# --------------------------------------------------------------------------- #
# Predictive BMI forecasting (USP)
# --------------------------------------------------------------------------- #

def test_forecast_unavailable_with_single_entry():
    forecast = bmi_logic.forecast_bmi_trend([_entry(0)])
    assert forecast["available"] is False


def test_forecast_unavailable_same_day_entries():
    history = [_entry(0, bmi=22.0), _entry(0, bmi=21.9)]
    forecast = bmi_logic.forecast_bmi_trend(history)
    assert forecast["available"] is False


def test_forecast_detects_falling_trend():
    history = [
        _entry(20, bmi=27.0),
        _entry(10, bmi=25.5),
        _entry(0, bmi=24.0),
    ]
    forecast = bmi_logic.forecast_bmi_trend(history)
    assert forecast["available"] is True
    assert forecast["trend_direction"] == "falling"
    assert forecast["bmi_change_per_week"] < 0


def test_forecast_detects_rising_trend():
    history = [
        _entry(20, bmi=20.0),
        _entry(10, bmi=21.0),
        _entry(0, bmi=22.0),
    ]
    forecast = bmi_logic.forecast_bmi_trend(history)
    assert forecast["trend_direction"] == "rising"


def test_forecast_goal_eta_only_when_moving_toward_goal():
    # Weight is trending down and the goal is below current weight -> should
    # produce a real ETA.
    history = [
        _entry(20, weight=80.0, bmi=27.0),
        _entry(10, weight=77.0, bmi=25.8),
        _entry(0, weight=74.0, bmi=24.6),
    ]
    forecast = bmi_logic.forecast_bmi_trend(history, goal_weight_kg=70.0)
    assert forecast["goal_eta_days"] is not None
    assert forecast["goal_eta_days"] > 0


def test_forecast_no_eta_when_moving_away_from_goal():
    history = [
        _entry(20, weight=70.0, bmi=22.0),
        _entry(10, weight=72.0, bmi=22.7),
        _entry(0, weight=74.0, bmi=23.4),
    ]
    forecast = bmi_logic.forecast_bmi_trend(history, goal_weight_kg=65.0)
    assert forecast["goal_eta_days"] is None


# --------------------------------------------------------------------------- #
# Transparent Health Score
# --------------------------------------------------------------------------- #

def test_health_score_within_bounds():
    history = [_entry(3), _entry(2), _entry(1), _entry(0)]
    forecast = bmi_logic.forecast_bmi_trend(history)
    score = bmi_logic.compute_health_score(22.0, "Normal", 4, history, forecast)
    assert 0 <= score["score"] <= 100
    assert sum(c["max"] for c in score["components"]) in (80, 100)


def test_health_score_components_sum_matches_totals():
    history = [_entry(1), _entry(0)]
    forecast = {"available": False}
    goal_progress = {"percent": 50}
    score = bmi_logic.compute_health_score(22.0, "Normal", 1, history, forecast, goal_progress)
    labels = [c["label"] for c in score["components"]]
    assert "Goal progress" in labels
    assert sum(c["max"] for c in score["components"]) == 100


def test_health_score_perfect_bmi_scores_higher_than_extreme_bmi():
    history = [_entry(2), _entry(1), _entry(0)]
    forecast = {"available": False}
    good = bmi_logic.compute_health_score(21.7, "Normal", 3, history, forecast)
    bad = bmi_logic.compute_health_score(38.0, "Obese", 3, history, forecast)
    assert good["score"] > bad["score"]
