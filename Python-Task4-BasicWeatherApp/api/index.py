"""Vercel entrypoint.

Vercel's Python builder looks for a WSGI-callable named `app` in a file
under /api. This just re-exports the real Flask app defined in the
project root's app.py, so app.py itself stays a normal, independently
runnable Flask app for local development (`python app.py`).
"""

import sys
from pathlib import Path

# Make the project root importable (Vercel invokes this file directly,
# so the root isn't automatically on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app  # noqa: E402
