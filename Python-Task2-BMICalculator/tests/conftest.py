"""tests/conftest.py — shared pytest fixtures."""

import os
import tempfile
import pytest


@pytest.fixture
def app(monkeypatch):
    """A Flask app wired to a throwaway SQLite file, fresh for every test."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    from app.config import Config
    monkeypatch.setattr(Config, "SQLITE_PATH", db_path)
    monkeypatch.setattr(Config, "DATABASE_URL", None)
    monkeypatch.setattr(Config, "GEMINI_API_KEY", "")

    # Reset the module-level USE_POSTGRES flag that db.py computed at import time.
    import app.models.db as db_module
    monkeypatch.setattr(db_module, "USE_POSTGRES", False)

    from app import create_app
    flask_app = create_app()
    flask_app.config.update(TESTING=True)

    yield flask_app

    os.remove(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def onboarded_client(client):
    """A client with an active session for a fresh user with a profile but no records yet."""
    client.post("/onboarding", data={
        "username": "TestUser",
        "height_m": "1.75",
        "age": "30",
        "sex": "male",
        "activity_level": "moderate",
        "goal_type": "lose",
        "target_weight": "70",
    })
    return client
