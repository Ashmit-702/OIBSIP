"""app/routes/reports.py — GET /api/report (PDF), GET /api/export (CSV)."""

from flask import Blueprint, Response, jsonify

from app.models import user_repository, health_repository, goal_repository
from app.services import report_service, goal_service, insight_service
from app.utils.session_helper import require_current_username
from app.utils.errors import NotFoundError

reports_bp = Blueprint("reports_api", __name__)


@reports_bp.route("/api/report")
def download_report():
    username = require_current_username()
    records = health_repository.get_records(username)
    if not records:
        raise NotFoundError("No records found. Log a check-in before generating a report.")

    profile = user_repository.get_profile(username)
    latest = records[-1]
    goal = goal_repository.get_goal(username)
    goal_summary = goal_service.build_goal_summary(records, goal) if goal else None
    insights = insight_service.generate_insights(records)

    pdf_bytes = report_service.generate_pdf_report(username, profile, latest, records, goal_summary, insights)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={username}_vitals_report.pdf"}
    )


@reports_bp.route("/api/export")
def export_csv():
    username = require_current_username()
    records = health_repository.get_records(username)
    if not records:
        raise NotFoundError("No records found for this user.")

    csv_data = report_service.generate_csv_export(records)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={username}_vitals_history.csv"}
    )
