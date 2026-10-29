"""AICTE Approva — runnable Flask integration service.

The complete interactive approval workspace ships as index.html. This service
serves that workspace and exposes the documented, strictly read-only adapter
API. It contains no endpoint that can change an application or make a decision.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
DB_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "instance/approva.db")

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "development-only-change-me"),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)


def db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise RuntimeError("Database not found. Run `python seed.py` first.")
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def rows(query: str, params: tuple = ()) -> list[dict]:
    with db() as connection:
        return [dict(r) for r in connection.execute(query, params).fetchall()]


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def workspace():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/api/v1/health")
def health():
    try:
        with db() as connection:
            connection.execute("SELECT 1").fetchone()
        state = "ok"
    except Exception:
        state = "database_not_seeded"
    return jsonify(
        status="ok",
        service="aicte-approva",
        version="2.4.1",
        database=state,
        decision_authority="manual-officer-only",
        timestamp=datetime.now().astimezone().isoformat(),
    )


def read_access() -> bool:
    expected = os.getenv("API_READ_TOKEN", "").strip()
    if not expected:
        return True
    return request.headers.get("X-API-Key", "") == expected


@app.before_request
def protect_read_apis():
    if request.path.startswith("/api/v1/") and request.path != "/api/v1/health":
        if not read_access():
            return jsonify(error="Read token required", code="AUTH_READ_REQUIRED"), 401
        if request.method != "GET":
            return jsonify(error="Adapter is read-only", code="READ_ONLY"), 405
    return None


@app.get("/api/v1/institutions")
def institutions():
    region = request.args.get("region")
    sql = """SELECT id, code, name, city, region, type, new_institution
             FROM institutions"""
    params = ()
    if region:
        sql += " WHERE region = ?"
        params = (region,)
    data = rows(sql + " ORDER BY name", params)
    return jsonify(data=data, meta={"total": len(data), "read_only": True})


@app.get("/api/v1/applications")
def applications():
    clauses, params = [], []
    for field, column in (("region", "region"), ("stage", "stage"), ("status", "status")):
        value = request.args.get(field)
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""SELECT id, institution_id, institution_name, region, type, stage,
                     status, route_code, route_name, days_in_stage, sla_days,
                     owner, committee, submitted_on
              FROM applications {where} ORDER BY days_in_stage DESC"""
    data = rows(sql, tuple(params))
    limit = min(max(request.args.get("per_page", 50, type=int), 1), 150)
    page = max(request.args.get("page", 1, type=int), 1)
    start = (page - 1) * limit
    return jsonify(
        data=data[start:start + limit],
        meta={"page": page, "per_page": limit, "total": len(data), "read_only": True},
    )


@app.get("/api/v1/applications/<path:application_id>")
def application(application_id: str):
    record = rows("SELECT * FROM applications WHERE id = ?", (application_id,))
    if not record:
        return jsonify(error="Application not found"), 404
    movements = rows(
        "SELECT created_at, actor, role, action, note FROM movements WHERE application_id = ? ORDER BY id",
        (application_id,),
    )
    item = record[0]
    item["movements"] = movements
    return jsonify(item)


@app.get("/api/v1/evc-sessions")
def evc_sessions():
    data = rows(
        """SELECT id, application_id, institution_id, institution_name, committee,
                  visit_date, visit_time, mode, status, new_institution
           FROM evc_sessions ORDER BY visit_date"""
    )
    return jsonify(data=data, meta={"total": len(data), "read_only": True})


@app.get("/api/v1/compliance/undertakings")
def undertakings():
    data = rows(
        """SELECT id, institution_id, institution_name, category, condition, due_date,
                  status, evidence_required, verified_by, verified_on
           FROM undertakings ORDER BY due_date"""
    )
    return jsonify(data=data, meta={"total": len(data), "read_only": True})


@app.get("/api/v1/documents/validity")
def document_validity():
    data = rows(
        """SELECT id, institution_id, institution_name, name, category, issue_date,
                  expiry_date, status, alert_window
           FROM documents ORDER BY expiry_date"""
    )
    return jsonify(data=data, meta={"total": len(data), "read_only": True})


@app.get("/api/v1/reports/pendency")
def pendency():
    active = rows(
        """SELECT stage, COUNT(*) AS cases,
                  ROUND(AVG(days_in_stage), 1) AS avg_age,
                  SUM(CASE WHEN days_in_stage > sla_days THEN 1 ELSE 0 END) AS breached
           FROM applications
           WHERE stage NOT IN ('Approved', 'Returned', 'Rejected')
           GROUP BY stage ORDER BY cases DESC"""
    )
    return jsonify(
        generated_at=datetime.now().astimezone().isoformat(),
        by_stage=active,
        total_active=sum(row["cases"] for row in active),
        read_only=True,
        decision_safeguard="System output only; decisions require a competent authority.",
    )


def daily_scan() -> None:
    """APScheduler entry point: read-only operational scan logging."""
    try:
        counts = rows(
            """SELECT
                (SELECT COUNT(*) FROM applications) applications,
                (SELECT COUNT(*) FROM undertakings WHERE status != 'Compliant') open_undertakings,
                (SELECT COUNT(*) FROM documents WHERE expiry_date <= date('now', '+30 day')) expiring_documents"""
        )
        print(f"[APScheduler {datetime.now().isoformat(timespec='seconds')}] scan: {counts[0]}")
    except Exception as error:  # pragma: no cover - operational fallback
        print(f"[APScheduler] scan skipped: {error}")


def start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
        scheduler.add_job(daily_scan, "cron", hour=6, minute=0, id="daily_alert_scan", replace_existing=True)
        scheduler.start()
        app.extensions["scheduler"] = scheduler
    except Exception as error:  # scheduler is optional if the host restricts threads
        print(f"[startup] APScheduler unavailable: {error}")


if __name__ == "__main__":
    if not DB_PATH.exists():
        raise SystemExit("Database missing. Run `python seed.py` first.")
    start_scheduler()
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "5000")), debug=False)
