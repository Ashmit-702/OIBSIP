# Station — a Python-backed weather instrument

A weather app with a Flask backend and a vanilla JS/CSS frontend styled like a
physical weather-station instrument panel (barograph trend line, sun-path arc,
air-quality gauge) instead of the usual "card with an icon" template.

## Task checklist

| Requirement | Where it's implemented |
|---|---|
| City/ZIP input | `templates/index.html` search box; `looksLikeZip()` in `static/js/app.js` auto-detects which one you typed |
| Weather API | OpenWeatherMap (current weather + forecast + air quality) via `services/weather_service.py` |
| Temperature | `current.temp` / `current.feels_like` |
| Humidity | `current.humidity` |
| Condition | `current.description` + icon |
| Wind speed | `current.wind_speed` (+ compass direction) |
| API error handling | `services/exceptions.py` custom exceptions → mapped to HTTP status in `app.py`; frontend shows a real error banner |
| Empty input validation | Client-side (`static/js/app.js`, before the request is even sent) and server-side (`app.py`, whitespace-only input is rejected too) |

The frontend never talks to OpenWeatherMap directly — it only calls this
server's own `/api/*` routes, so the API key stays server-side.


## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then paste your OpenWeatherMap key into .env
python app.py                # serves at http://localhost:5000
```

Get a free key at https://openweathermap.org/api (new keys can take up to an
hour to activate).

## Run the tests

```bash
pytest -v
```

## Deploying to Vercel

The repo already includes `vercel.json` and `api/index.py`, which is the
entrypoint structure Vercel's Python builder expects. Two things matter:

1. **Set the environment variable in the Vercel dashboard**, not just in
   `.env` (which isn't deployed): Project → Settings → Environment Variables
   → add `OPENWEATHER_API_KEY`.
2. **The database is ephemeral on Vercel.** Serverless functions run on a
   read-only filesystem except `/tmp`, so `services/db.py` detects that
   (`VERCEL` env var) and writes there instead — search history will work,
   but resets between cold starts. That's expected on serverless; use a
   hosted DB (Postgres, Turso, etc.) instead of SQLite if persistent history
   matters for the deployed version. The app also now degrades gracefully:
   if the DB layer fails to initialize for any reason, weather lookups keep
   working and history silently returns empty instead of crashing the whole
   function.

## Project layout

```
app.py                        Flask routes, error → HTTP status mapping
services/
  weather_service.py          Orchestrates OpenWeatherMap calls, concurrency, shaping
  cache.py                    Thread-safe TTL cache
  db.py                       SQLite-backed search history
  exceptions.py                Custom exception hierarchy
templates/index.html          Jinja shell
static/css/style.css          Instrument-panel styling
static/js/app.js              Frontend logic (fetch, render, SVG drawing)
tests/test_weather_service.py Unit tests (pure logic + mocked HTTP)
```

## What this demonstrates (good for a Python internship task / interview)

- **Multi-endpoint API orchestration**: current weather, 5-day forecast, and
  air quality are three separate OpenWeatherMap endpoints, chained together
  (forecast + air quality need coordinates from the first call).
- **Concurrency, used twice, for two different reasons**: the forecast and
  air-quality calls for a single city run in parallel via
  `ThreadPoolExecutor` (`weather_service.get_weather`), and pinned-city
  dashboard lookups for *multiple* cities also run concurrently
  (`app.api_pinned_list`) — the same pattern applied at two different
  scopes, worth pointing out explicitly in an interview.
- **A multi-city pinned dashboard**: pin up to 6 cities (persisted in
  SQLite), and every page load re-fetches all of them concurrently so the
  strip at the top always shows live temperatures.
- **Rule-based decision logic**: `advisory()` turns condition code, wind
  speed, temperature, and AQI into a one-line "what should I do" message —
  simple, testable, deterministic logic instead of hardcoded strings.
- **Thread-safe caching**: a small TTL cache with a `threading.Lock`, since
  Flask's dev server (and most WSGI servers) can handle concurrent requests
  and the free OpenWeatherMap tier has a strict rate limit.
- **A real database, not just in-memory state**: recent searches and pinned
  cities persist in SQLite via the stdlib `sqlite3` module, with
  parameterized queries only.
- **Custom exception hierarchy**: `CityNotFoundError`, `InvalidAPIKeyError`,
  `UpstreamTimeoutError` map cleanly to HTTP status codes in the Flask layer,
  instead of one generic try/except.
- **Server-side date/timezone math**: sunrise/sunset, local time, and "how
  far through daylight are we" are computed in Python with
  `datetime`/`timezone`, not guessed at in JavaScript.
- **Security-conscious architecture**: the API key lives in an environment
  variable (stripped of stray whitespace) and is never sent to the browser
  — the frontend is a pure consumer of our own JSON API.
- **37 tests with mocked HTTP**: unit tests for pure logic (compass
  conversion, sky classification, advisory rules, cache expiry) plus
  Flask-test-client integration tests for every route, including the
  pinned-cities CRUD flow. No network access or real API key needed to run
  the suite.

## Frontend highlights

- A live **sky background** (stars/moon, drifting clouds, falling rain or
  snow, hazy fog bands) that changes with the real weather condition and
  time of day — driven by `sky_theme`, computed server-side.
- An **hourly strip** and **5-day forecast**, a **sun-path arc**, an
  **air-quality gauge**, and a **pinned-cities dashboard**, all on one page.
- A loading skeleton and a real status/error banner instead of plain text.

## Ideas to push it further

- Swap SQLite for Postgres and add a `Dockerfile` for deployment.
- Add rate limiting per client IP (e.g. `Flask-Limiter`) in front of `/api/weather`.
- Add weather alerts (One Call 3.0's `alerts` field) as a banner when severe
  weather is active for the searched location.
