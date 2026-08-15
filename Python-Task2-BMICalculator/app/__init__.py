"""
app/__init__.py
Application factory: wires together config, database init, blueprints, and
error handlers. Keeping this separate from a flat entrypoint file is what makes the
route/service/model layers independently testable.
"""

import os

from flask import Flask

from app.config import Config
from app.models.db import init_db
from app.utils.errors import register_error_handlers

# Absolute paths, computed from this file's location, so template/static
# resolution doesn't depend on the process's current working directory --
# serverless platforms don't always invoke from the project root.
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_APP_DIR)
_TEMPLATE_DIR = os.path.join(_PROJECT_ROOT, "templates")
_STATIC_DIR = os.path.join(_PROJECT_ROOT, "static")


def create_app(config_object: type = Config) -> Flask:
    app = Flask(
        __name__,
        template_folder=_TEMPLATE_DIR,
        static_folder=_STATIC_DIR,
    )
    app.config.from_object(config_object)
    app.secret_key = config_object.SECRET_KEY

    # Initialise the database schema once at startup. Don't crash the whole
    # app if this fails -- surface the error per-request instead, so a
    # transient DB outage (or a first-deploy schema hiccup) doesn't take
    # down routes that don't need it yet.
    try:
        init_db()
    except Exception as e:
        app.logger.warning(f"[startup warning] {e}")

    register_error_handlers(app)

    from app.routes.pages import pages_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.health import health_bp
    from app.routes.analytics import analytics_bp
    from app.routes.goals import goals_bp
    from app.routes.insights import insights_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(reports_bp)

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    return app
