"""
bmi_logic.py
Core BMI calculation, category classification, and AI-generated personalized
health insights via the Gemini API.

The Gemini integration is fully optional: if no GEMINI_API_KEY is set, the
app still works perfectly for calculation + history + trends. This means a
missing/invalid key never breaks the core feature.
"""

import os
import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


class ValidationError(Exception):
    """Raised when user input fails validation, so the API can return a 400 with a clear message."""
    pass


def calculate_bmi(weight_kg: float, height_m: float) -> float:
    if weight_kg <= 0 or height_m <= 0:
        raise ValidationError("Weight and height must be positive numbers.")
    if height_m > 3:
        raise ValidationError("Height looks too large — please enter height in metres (e.g. 1.75).")
    bmi = weight_kg / (height_m ** 2)
    return round(bmi, 2)


def classify_bmi(bmi: float) -> str:
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"


def get_ai_insights(username: str, bmi: float, category: str, history: list) -> dict:
    """
    Calls Gemini to generate a short, personalized, non-alarming health note.
    Returns a dict: {"available": bool, "message": str}
    Never raises — always degrades gracefully so the UI never breaks because
    of an API/network issue.
    """
    if not GEMINI_API_KEY:
        return {
            "available": False,
            "message": "AI insights are turned off. Add a GEMINI_API_KEY environment "
                       "variable to enable personalized suggestions."
        }

    trend_note = ""
    if len(history) >= 2:
        first_bmi = history[0]["bmi"]
        last_bmi = history[-1]["bmi"]
        direction = "increased" if last_bmi > first_bmi else "decreased" if last_bmi < first_bmi else "stayed steady"
        trend_note = f"Over their {len(history)} logged entries, this user's BMI has {direction} " \
                     f"from {first_bmi} to {last_bmi}."

    prompt = (
        f"You are a friendly, encouraging health assistant inside a BMI tracking app. "
        f"A user named {username} just logged a BMI of {bmi}, classified as '{category}'. "
        f"{trend_note} "
        f"Write a short (3-4 sentences), warm, non-judgemental note with one practical "
        f"suggestion (diet or activity) suited to this category. Do not give medical "
        f"diagnoses. Do not mention that you are an AI model."
    )

    try:
        response = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return {"available": True, "message": text.strip()}
    except requests.exceptions.Timeout:
        return {"available": False, "message": "AI insight request timed out. Try again in a moment."}
    except requests.exceptions.RequestException as e:
        return {"available": False, "message": f"Could not reach the AI service right now ({e})."}
    except (KeyError, IndexError):
        return {"available": False, "message": "AI service returned an unexpected response."}
