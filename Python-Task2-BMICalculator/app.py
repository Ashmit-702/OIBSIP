"""
app.py
Thin WSGI entrypoint. Vercel's Python builder looks for a top-level `app.py`
exposing a module-level `app` object, so this stays as a one-line shim over
the real application factory in app/__init__.py.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
