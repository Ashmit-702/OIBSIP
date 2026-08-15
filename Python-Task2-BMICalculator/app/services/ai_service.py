"""
app/services/ai_service.py
Optional AI Wellness Coach. Talks to the Gemini API using ONLY structured,
pre-computed metrics (never raw database rows) so the model can't see more
than a short summary, and the API key never leaves the server.

Fully optional: if GEMINI_API_KEY is unset, or the request fails for any
reason (timeout, rate limit, bad response), this transparently returns
available=False and the caller falls back to the deterministic insight
engine — the app never depends on this for core functionality.
"""

import time
import requests

from app.config import Config

GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

SYSTEM_INSTRUCTION = (
    "You are a general wellness note-writer inside a fitness tracking app called Vitals+. "
    "You will be given a small set of structured metrics about a user's logged weight, BMI, "
    "activity, sleep, hydration, and goal progress. Write a short (3-4 sentence), warm, "
    "non-judgemental observation about their recent trend, grounded ONLY in the metrics given. "
    "Rules you must always follow: "
    "1) Never diagnose any disease or medical condition. "
    "2) Never prescribe medication, supplements, or a specific diet plan. "
    "3) Never state medical certainty — this is general wellness guidance, not medical advice. "
    "4) Never invent numbers not present in the metrics. "
    "5) Do not mention that you are an AI model."
)


def _build_prompt(metrics: dict) -> str:
    lines = [f"{k}: {v}" for k, v in metrics.items() if v is not None]
    return SYSTEM_INSTRUCTION + "\n\nMetrics:\n" + "\n".join(lines)


def get_ai_wellness_note(metrics: dict) -> dict:
    """
    metrics: a flat dict of pre-computed values, e.g.
      {"bmi": 23.4, "weight_trend": "falling 0.3kg/week", "activity_logging_pct": 80,
       "avg_sleep_hours": 7.2, "avg_hydration_l": 2.1, "goal_progress_pct": 62}

    Returns {"available": bool, "message": str|None, "reason": str|None}. Never raises.
    """
    if not Config.GEMINI_API_KEY:
        return {"available": False, "message": None, "reason": "AI coach is not configured."}

    prompt = _build_prompt(metrics)
    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(
                f"{GEMINI_URL}?key={Config.GEMINI_API_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=8,
            )
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < max_attempts:
                    time.sleep(1.0)
                    continue
                return {"available": False, "message": None, "reason": "AI coach is temporarily unavailable."}

            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"available": True, "message": text.strip(), "reason": None}

        except requests.exceptions.RequestException:
            if attempt < max_attempts:
                continue
            return {"available": False, "message": None, "reason": "AI coach is temporarily unavailable."}
        except (KeyError, IndexError, ValueError):
            return {"available": False, "message": None, "reason": "AI coach returned an unexpected response."}

    return {"available": False, "message": None, "reason": "AI coach is temporarily unavailable."}
