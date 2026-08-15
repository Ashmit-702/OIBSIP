"""
app/services/demo_service.py
Seeds a clearly-labeled demo profile with synthetic-but-plausible history so
the dashboard can be explored immediately without manual data entry. Demo
data is stored under the fixed username "Demo" and is only ever created via
an explicit user action (clicking "View Demo") — it never mixes into a real
user's account.
"""

import random
from datetime import date, timedelta

from app.models import user_repository, health_repository, goal_repository
from app.services.bmi_service import calculate_bmi, classify_bmi

DEMO_USERNAME = "Demo"


def seed_demo_data(force: bool = False) -> None:
    if not force and user_repository.profile_exists(DEMO_USERNAME):
        return

    height_m = 1.72
    user_repository.upsert_profile(
        DEMO_USERNAME, height_m=height_m, age=27, sex="male",
        activity_level="moderate", goal_type="lose",
        target_weight_kg=72.0, target_date=(date.today() + timedelta(days=60)).isoformat()
    )
    goal_repository.set_goal(DEMO_USERNAME, "lose", 72.0,
                              (date.today() + timedelta(days=60)).isoformat())

    health_repository.delete_all_records(DEMO_USERNAME)

    rng = random.Random(42)  # deterministic demo data
    start_weight = 81.5
    weight = start_weight
    today = date.today()

    for i in range(60, -1, -1):
        d = today - timedelta(days=i)
        # Gentle downward trend with realistic day-to-day noise, logged ~80% of days.
        if rng.random() < 0.8:
            weight -= rng.uniform(0.0, 0.09)
            weight += rng.uniform(-0.15, 0.1)
            weight = round(weight, 1)
            bmi = calculate_bmi(weight, height_m)
            category = classify_bmi(bmi)
            health_repository.add_record(
                DEMO_USERNAME, d.isoformat(), weight, height_m, bmi, category,
                waist_cm=round(88 - (start_weight - weight) * 0.6, 1),
                water_l=round(rng.uniform(1.6, 3.0), 1),
                steps=rng.choice([None, rng.randint(3500, 11000)]),
                sleep_hours=round(rng.uniform(5.8, 8.4), 1),
                calories=rng.choice([None, rng.randint(1900, 2600)]),
            )
