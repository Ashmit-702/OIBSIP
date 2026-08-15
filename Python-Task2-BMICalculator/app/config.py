"""
app/config.py
Centralised, environment-driven configuration. No secrets are hardcoded here —
everything sensitive is read from the environment (see .env.example).
"""

import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DATABASE_URL = os.environ.get("DATABASE_URL")  # Postgres, if set; else SQLite fallback
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    ON_VERCEL = bool(os.environ.get("VERCEL"))

    # Vercel's deployment filesystem is read-only except /tmp. /tmp is ephemeral
    # between cold starts, so DATABASE_URL (a real Postgres) is required for
    # durable persistence in that environment. SQLite is used for local dev.
    if ON_VERCEL:
        SQLITE_PATH = "/tmp/vitals.db"
    else:
        SQLITE_PATH = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vitals.db"
        )
