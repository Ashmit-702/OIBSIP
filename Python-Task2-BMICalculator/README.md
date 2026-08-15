# VITALS+

### Personal Health & Fitness Analytics Platform

VITALS+ is a wellness and fitness tracking platform: BMI calculation, weight
history, daily check-ins, goal tracking, analytics, deterministic health
insights, an optional AI wellness coach, and downloadable PDF/CSV reports —
built on Flask with a clean, layered Python backend.

**VITALS+ is a wellness/fitness tracking tool. It is not a medical device
and does not diagnose conditions or prescribe treatment.**

---

## Features

- **BMI calculator** — `BMI = weight (kg) / height (m)²`, classified into
  Underweight / Normal / Overweight / Obese, with input validation on every
  field (positive numbers, sane ranges, correct units).
- **Onboarding** — height, weight, age, sex, activity level, and a goal,
  captured once and used everywhere downstream.
- **Dashboard** — BMI, weight (with month-over-month change), goal progress,
  and a transparent Wellness Consistency Score, all computed from stored data.
- **Daily check-ins** — weight, water, steps, sleep, optional waist/calories.
- **Weight history** — searchable, filterable (7D/30D/90D/1Y/All) table with
  edit/delete, current/starting/target weight, highs/lows/averages, and rate
  of change.
- **Analytics** — weight & BMI trend charts (Chart.js), weekly logging
  consistency bars, and a linear-regression trend forecast with an ETA to
  goal.
- **Goals** — target weight/date, progress %, required weekly pace, and an
  estimated completion date based on your actual trend (not a guess).
- **Insight engine** — deterministic, plain-language observations generated
  from real history (`app/services/insight_service.py`) — no LLM required.
- **Optional AI Wellness Coach** — feeds a small set of *pre-computed*
  metrics (never raw rows) to Gemini for a short, non-diagnostic note. Fully
  optional; the app works completely without it.
- **Reports** — a downloadable PDF (baseline, current metrics, goal
  progress, a weight-trend chart, insights, and a 30-row history table) and
  a raw CSV export.
- **Demo mode** — one click seeds a realistic 60-day sample profile so the
  app can be explored instantly, clearly separate from real user data.
- **Dark mode**, responsive sidebar/bottom-nav layout, empty states, loading
  skeletons, and toasts for every async action.

---

## What already existed vs. what changed

This project began as a well-built single-page Flask app (`app.py`,
`bmi_logic.py`, `db.py`, `report.py`, one `index.html`) with solid BMI/BMR
math, a hybrid AI+deterministic insight engine, parameterized SQL, and a
decent pytest suite. That logic is preserved — it's been **ported and
reorganised**, not thrown away.

**Changed:** the project was restructured from 4 flat files into a layered
package (`app/routes` / `app/services` / `app/models` / `app/utils`), the
single-page UI became a 7-page SaaS-style product (landing → onboarding →
dashboard → analytics/goals/history/reports) with a sidebar/mobile-nav shell,
health_records gained daily-check-in fields (water/steps/sleep/calories), a
goals table and transparent scoring/forecasting services were added, the
test suite grew from ~15 tests covering one module to 119 tests across nine
files, and a documented PDF-generation bug (see below) was found and fixed
during testing.

---

## Architecture

```
app/
  __init__.py            # application factory
  config.py               # env-driven configuration
  routes/                 # HTTP layer only — no business logic
    pages.py               # landing/onboarding/dashboard/analytics/goals/history/reports
    dashboard.py            # GET /api/dashboard
    health.py                # /api/health CRUD
    analytics.py              # GET /api/analytics
    goals.py                   # /api/goals
    insights.py                  # GET /api/insights
    reports.py                    # /api/report (PDF), /api/export (CSV)
  services/                # business logic — pure functions, unit-testable
    bmi_service.py           # BMI, BMR, body fat %, hydration target
    analytics_service.py      # trend stats, forecasting (linear regression)
    goal_service.py            # progress %, required pace, ETA
    score_service.py             # Wellness Consistency Score
    insight_service.py            # deterministic insight generation
    ai_service.py                   # optional Gemini wellness coach
    report_service.py                # PDF/CSV generation
    demo_service.py                   # sample data seeding
  models/                  # data access — the only layer that touches SQL
    db.py                    # connection management + schema (SQLite/Postgres)
    user_repository.py        # profile/onboarding data
    health_repository.py       # weight/check-in records
    goal_repository.py          # goals
  utils/
    validators.py            # input validation, shared by every route
    errors.py                  # custom exceptions + Flask error handlers
    session_helper.py           # lightweight name-based identity
templates/                 # Jinja2 pages + shared base.html shell
static/
  css/style.css             # design tokens, layout, components, responsive
  js/                        # one file per page + shared common.js
tests/                    # 119 pytest tests across 6 files
app.py                    # thin WSGI entrypoint (Vercel looks for this)
run.py                    # local dev entrypoint
```

Separation of concerns: **routes** validate input and call services;
**services** contain all business logic and are pure functions with no
Flask or database imports (trivially unit-testable); **models** are the only
layer that constructs SQL, and every query is parameterized.

---

## Tech stack

- **Backend:** Flask 3, Python 3.12
- **Database:** SQLite (local dev) or PostgreSQL (production, via
  `DATABASE_URL`) — auto-detected at startup
- **PDF generation:** fpdf2 (pure Python, no native dependencies — reliable
  on serverless runtimes)
- **Charts:** Chart.js (CDN)
- **Optional AI:** Google Gemini (`gemini-2.0-flash`) via the REST API
- **Testing:** pytest + Flask's test client

---

## Database design

Three tables, created automatically on first run (`app/models/db.py`):

| Table | Purpose | Key columns |
|---|---|---|
| `users` | Onboarding baseline profile | `username` (PK), `height_m`, `age`, `sex`, `activity_level`, `goal_type`, `target_weight_kg`, `target_date` |
| `health_records` | Every weight entry / daily check-in | `id`, `username`, `entry_date`, `weight_kg`, `bmi`, `category`, `waist_cm`, `water_l`, `steps`, `sleep_hours`, `calories` |
| `goals` | Current active goal | `username` (PK), `goal_type`, `target_weight_kg`, `target_date` |

`health_records` intentionally backs both "weight history" and "daily
check-ins" — a check-in is just a record with the optional wellness fields
filled in, avoiding a redundant second table for the same timeline.

Identity is a lightweight, name-based profile stored in a signed session
cookie (no passwords) — appropriate for a demo/tracking tool, documented
here rather than presented as production authentication.

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/dashboard` | Summary cards for the Overview page |
| GET | `/api/health/history?window=` | List records, optional time filter |
| POST | `/api/health` | Create a check-in / weight entry |
| PUT | `/api/health/<id>` | Update a record |
| DELETE | `/api/health/<id>` | Delete a record |
| GET | `/api/analytics?window=` | Chart series + trend statistics |
| GET | `/api/goals` | Current goal + progress summary |
| POST | `/api/goals` | Set/update the goal |
| DELETE | `/api/goals` | Clear the goal |
| GET | `/api/insights` | Deterministic insights + optional AI note |
| GET | `/api/report` | Download PDF health report |
| GET | `/api/export` | Download CSV history export |

All endpoints return JSON with a consistent `{"error": "..."}` shape on
failure, and use standard status codes (400 invalid input, 404 not found,
500 unexpected error — never a raw stack trace).

---

## Testing

```bash
pip install -r requirements-dev.txt --break-system-packages
pytest tests/ -v
```

**119 tests, all passing**, across:

- `test_bmi_service.py` — BMI formula correctness, all 4 category boundaries,
  BMR/calorie/hydration estimates, invalid-input rejection
- `test_validators.py` — every validator's happy path and edge cases
  (negative/zero/non-numeric/oversized/malformed input)
- `test_analytics_service.py` — trend stats, time-window filtering, logging
  consistency, streaks, linear-regression forecasting
- `test_goal_service.py` — progress %, required pace, ETA, infeasible-pace
  detection
- `test_insight_and_score.py` — insight text is grounded in real computed
  numbers; wellness score stays in bounds and omits components with no data
- `test_api.py` — full HTTP round-trips through the Flask test client:
  onboarding validation, health CRUD, dashboard/goals/report/CSV endpoints,
  security headers

A real bug was found and fixed during this testing pass: fpdf2's
`multi_cell(width=0, ...)` leaves the cursor at the right margin instead of
resetting to the left margin, so a second consecutive call collapsed to
zero available width and crashed report generation whenever there was more
than one insight. Fixed in `report_service.py` by explicitly resetting `x`
before each call; covered by `test_report_generates_pdf`.

---

## Setup instructions

```bash
git clone <your-repo-url>
cd OIBSIP-main
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env       # fill in optional values, see below
python run.py
```

Visit `http://localhost:5000`.

## Environment variables

| Variable | Required? | Purpose |
|---|---|---|
| `SECRET_KEY` | Recommended | Flask session signing key |
| `DATABASE_URL` | Optional | Postgres connection string. Without it, falls back to a local SQLite file — fine for dev, **not durable on Vercel** (its filesystem is read-only outside `/tmp`, which is wiped between cold starts) |
| `GEMINI_API_KEY` | Optional | Enables the AI Wellness Coach. Without it, the app runs fully on the deterministic insight engine |

No secrets are hardcoded anywhere; `.env` is git-ignored; `.env.example`
ships with placeholders only.

## Deployment (Vercel)

1. Push this repo to GitHub.
2. Import it in Vercel — `vercel.json` is already configured to build
   `app.py` with `@vercel/python` and serve `/static/*` directly.
3. In the Vercel project's Environment Variables, set `SECRET_KEY` and
   (strongly recommended) `DATABASE_URL` pointing at a free Postgres
   instance (e.g. [Neon](https://neon.tech) or
   [Supabase](https://supabase.com)) — without it, data will not persist
   between requests on Vercel's serverless filesystem.
4. Optionally set `GEMINI_API_KEY` to enable the AI coach.
5. Deploy.

---

## Future improvements

- Real authentication (the current name-based profile model is intentionally
  lightweight for a demo/tracking tool)
- Body measurement photos / progress photo timeline
- Push/email reminders for daily check-ins
- Multi-metric correlation insights (e.g. sleep vs. weight trend)
