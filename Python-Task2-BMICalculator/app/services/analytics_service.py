"""
app/services/analytics_service.py
Turns a raw list of health_records rows into the statistics and chart series
shown on the Analytics and History pages. Every number here is derived from
real stored data — nothing is hardcoded or randomly generated.
"""

from datetime import datetime, timedelta, date
from typing import Optional

TIME_FILTERS = {"7D": 7, "30D": 30, "90D": 90, "1Y": 365, "All": None}


def parse_entry_date(raw) -> date:
    if isinstance(raw, str):
        return datetime.strptime(raw, "%Y-%m-%d").date()
    return raw


def filter_by_window(records: list, window: str = "All") -> list:
    """Keep only records whose entry_date falls within the last N days of TIME_FILTERS."""
    days = TIME_FILTERS.get(window, None)
    if not days or not records:
        return records
    cutoff = date.today() - timedelta(days=days)
    return [r for r in records if parse_entry_date(r["entry_date"]) >= cutoff]


def weight_history_stats(records: list) -> dict:
    """Summary stats for the Weight History page. Expects oldest -> newest."""
    if not records:
        return {
            "has_data": False, "current_weight": None, "starting_weight": None,
            "total_change": None, "highest_weight": None, "lowest_weight": None,
            "average_weight": None, "weekly_rate": None, "monthly_rate": None,
        }

    weights = [r["weight_kg"] for r in records]
    starting = weights[0]
    current = weights[-1]
    total_change = round(current - starting, 1)

    first_date = parse_entry_date(records[0]["entry_date"])
    last_date = parse_entry_date(records[-1]["entry_date"])
    span_days = max((last_date - first_date).days, 1)

    weekly_rate = round((total_change / span_days) * 7, 2) if len(records) >= 2 else None
    monthly_rate = round((total_change / span_days) * 30, 2) if len(records) >= 2 else None

    return {
        "has_data": True,
        "current_weight": current,
        "starting_weight": starting,
        "total_change": total_change,
        "highest_weight": round(max(weights), 1),
        "lowest_weight": round(min(weights), 1),
        "average_weight": round(sum(weights) / len(weights), 1),
        "weekly_rate": weekly_rate,
        "monthly_rate": monthly_rate,
    }


def build_chart_series(records: list, metric: str = "weight_kg") -> dict:
    """Returns {labels: [...], values: [...]} for Chart.js, for the given metric."""
    labels = [r["entry_date"] for r in records]
    values = [r.get(metric) for r in records]
    return {"labels": labels, "values": values}


def compute_logging_consistency(records: list, window_days: int = 30) -> dict:
    """
    Percentage of days in the trailing window that have at least one logged
    entry. This is the deterministic basis for both the Analytics page and
    the "Consistency" component of the Wellness Consistency Score.
    """
    if not records:
        return {"percent": 0, "days_logged": 0, "window_days": window_days}

    cutoff = date.today() - timedelta(days=window_days - 1)
    logged_dates = {parse_entry_date(r["entry_date"]) for r in records if parse_entry_date(r["entry_date"]) >= cutoff}
    days_logged = len(logged_dates)
    percent = round(min(100, (days_logged / window_days) * 100))
    return {"percent": percent, "days_logged": days_logged, "window_days": window_days}


def compute_weekly_consistency_bars(records: list, weeks: int = 8) -> dict:
    """Number of distinct days logged per ISO week, most recent `weeks` weeks — for a bar chart."""
    today = date.today()
    buckets = []
    for i in range(weeks - 1, -1, -1):
        week_start = today - timedelta(days=today.weekday() + 7 * i)
        week_end = week_start + timedelta(days=6)
        label = week_start.strftime("%b %d")
        days_logged = len({
            parse_entry_date(r["entry_date"]) for r in records
            if week_start <= parse_entry_date(r["entry_date"]) <= week_end
        })
        buckets.append({"label": label, "days_logged": days_logged})
    return {"buckets": buckets}


def compute_streak(records: list) -> int:
    """Longest run of consecutive calendar days logged, ending at the most recent entry."""
    if not records:
        return 0
    dates = sorted({parse_entry_date(r["entry_date"]) for r in records})
    streak = best = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            streak += 1
            best = max(best, streak)
        elif (dates[i] - dates[i - 1]).days > 1:
            streak = 1
    return best


def _linreg(xs: list, ys: list):
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den if den else 0.0
    intercept = mean_y - slope * mean_x
    return slope, intercept


def forecast_trend(records: list, goal_weight_kg: Optional[float] = None,
                    days_ahead: int = 30) -> dict:
    """
    Fits a least-squares linear regression of weight (and BMI) over time using
    the user's own logged history, then projects it forward. If a goal weight
    is set, also estimates days remaining at the current rate of change.
    Requires at least 2 entries spanning at least 1 real day.
    """
    if len(records) < 2:
        return {"available": False, "reason": "Log at least 2 entries on different days to unlock forecasting."}

    t0 = parse_entry_date(records[0]["entry_date"])
    xs = [(parse_entry_date(r["entry_date"]) - t0).days for r in records]

    if max(xs) < 1:
        return {"available": False, "reason": "Log entries on at least two different days to unlock forecasting."}

    ys_weight = [r["weight_kg"] for r in records]
    ys_bmi = [r["bmi"] for r in records]

    weight_slope, weight_intercept = _linreg(xs, ys_weight)
    bmi_slope, bmi_intercept = _linreg(xs, ys_bmi)

    last_x = xs[-1]
    projected_x = last_x + days_ahead
    projected_weight = round(weight_slope * projected_x + weight_intercept, 1)
    projected_bmi = round(bmi_slope * projected_x + bmi_intercept, 2)

    trend_direction = "rising" if weight_slope > 0.01 else "falling" if weight_slope < -0.01 else "stable"

    result = {
        "available": True,
        "trend_direction": trend_direction,
        "weight_change_per_week": round(weight_slope * 7, 2),
        "bmi_change_per_week": round(bmi_slope * 7, 3),
        "projected_weight": projected_weight,
        "projected_bmi": max(projected_bmi, 5),
        "projected_days": days_ahead,
        "confidence": "higher" if len(records) >= 5 else "preliminary",
    }

    if goal_weight_kg and abs(weight_slope) > 0.001:
        current_weight = ys_weight[-1]
        remaining_kg = goal_weight_kg - current_weight
        moving_correct_direction = (remaining_kg > 0 and weight_slope > 0) or \
                                    (remaining_kg < 0 and weight_slope < 0)
        if moving_correct_direction:
            days_needed = abs(remaining_kg / weight_slope)
            eta_date = (date.today() + timedelta(days=days_needed)).isoformat()
            result["goal_eta_days"] = round(days_needed)
            result["goal_eta_date"] = eta_date
        else:
            result["goal_eta_days"] = None
            result["goal_eta_date"] = None

    return result
