"""app/utils/errors.py — custom exceptions and a shared Flask error-handler registrar."""

from flask import jsonify


class ValidationError(Exception):
    """Raised when user input fails validation -> maps to HTTP 400."""
    pass


class NotFoundError(Exception):
    """Raised when a requested record doesn't exist -> maps to HTTP 404."""
    pass


def register_error_handlers(app):
    from app.models.db import DatabaseError

    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        return jsonify({"error": str(e)}), 400

    @app.errorhandler(NotFoundError)
    def handle_not_found(e):
        return jsonify({"error": str(e)}), 404

    @app.errorhandler(DatabaseError)
    def handle_database_error(e):
        # Log full detail server-side only; DB errors can contain connection
        # strings or credentials and must never reach the client.
        app.logger.error(f"[db error] {e}")
        return jsonify({"error": "A storage error occurred. Please try again shortly."}), 500

    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(500)
    def handle_500(e):
        app.logger.error(f"[unexpected error] {e}")
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500
