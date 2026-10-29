"""Seed a deterministic SQLite database for the AICTE Approva reference service.

No real institutional or personal data is used. The full interactive workspace
is in index.html; this database backs the read-only adapter API in run.py.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "instance" / "approva.db"
TODAY = date.today()
SEED = 20260314

REGIONS = {
    "North": ("NOR", "P. Bansal"),
    "South": ("SOU", "K. Ramanathan"),
    "East": ("EAS", "M. Sengupta"),
    "West": ("WES", "A. Kulkarni"),
}

INSTITUTIONS = [
    ("Delhi Technical Campus", "New Delhi", "North", "Existing"),
    ("Chandigarh Institute of Engineering", "Chandigarh", "North", "Existing"),
    ("Uttarakhand Institute of Technology", "Dehradun", "North", "New institution"),
    ("Jaipur National Technical University", "Jaipur", "North", "Existing"),
    ("Amritsar College of Engineering", "Amritsar", "North", "Variant"),
    ("Noida Institute of Applied Sciences", "Noida", "North", "Existing"),
    ("Himachal Technical Institute", "Solan", "North", "New institution"),
    ("Ganga Institute of Technology", "Meerut", "North", "Extension of approval"),
    ("Lucknow School of Engineering", "Lucknow", "North", "Variant"),
    ("Shri Mata Vaishno Institute", "Jammu", "North", "Existing"),
    ("Vidyanagara Institute of Technology", "Bengaluru", "South", "Extension of approval"),
    ("Sri Venkateswara College of Engineering", "Tirupati", "South", "Existing"),
    ("Rajagiri School of Engineering", "Kochi", "South", "New institution"),
    ("PSNA Institute of Technology", "Dindigul", "South", "Existing"),
    ("Aditya Institute of Technology", "Coimbatore", "South", "Variant"),
    ("Hyderabad Institute of Technology", "Hyderabad", "South", "Extension of approval"),
    ("KLS Gogte Institute of Technology", "Belagavi", "South", "Existing"),
    ("Sona College of Technology", "Salem", "South", "Existing"),
    ("Vignan Institute of Engineering", "Visakhapatnam", "South", "New institution"),
    ("Mepco Institute of Technology", "Madurai", "South", "Variant"),
    ("Kalinga Institute of Engineering", "Bhubaneswar", "East", "Existing"),
    ("Bengal Institute of Technology", "Kolkata", "East", "Extension of approval"),
    ("Assam School of Engineering", "Guwahati", "East", "New institution"),
    ("Patna Institute of Technology", "Patna", "East", "Existing"),
    ("Utkal College of Engineering", "Rourkela", "East", "Variant"),
    ("Ranchi Technical College", "Ranchi", "East", "Existing"),
    ("Siliguri Institute of Technology", "Siliguri", "East", "New institution"),
    ("Institute of Engineering and Management", "Gangtok", "East", "Extension of approval"),
    ("Buxi Institute of Technology", "Jamshedpur", "East", "Existing"),
    ("Bihar College of Engineering", "Bhagalpur", "East", "Variant"),
    ("Pune Institute of Business and Technology", "Pune", "West", "Existing"),
    ("Mumbai School of Engineering", "Mumbai", "West", "Extension of approval"),
    ("Ahmedabad Institute of Technology", "Ahmedabad", "West", "Existing"),
    ("Vadodara Institute of Technology", "Vadodara", "West", "New institution"),
    ("Nagpur Institute of Technology", "Nagpur", "West", "Variant"),
    ("Kolhapur Institute of Engineering", "Kolhapur", "West", "Existing"),
    ("Goa College of Engineering", "Ponda", "West", "New institution"),
    ("Sinhgad Institute of Technology", "Solapur", "West", "Existing"),
    ("Indira Institute of Engineering", "Nashik", "West", "Variant"),
    ("Thane School of Engineering", "Thane", "West", "Existing"),
]

ROUTES = [
    ("WF-S", "Only scrutiny", ["Scrutiny"], 10),
    ("WF-SE", "Scrutiny + EVC", ["Scrutiny", "EVC"], 18),
    ("WF-ES", "EVC + SAC/SHC", ["EVC", "SAC/SHC"], 21),
    ("WF-E", "Only EVC", ["EVC"], 18),
    ("WF-SES", "Scrutiny + EVC + SAC/SHC", ["Scrutiny", "EVC", "SAC/SHC"], 28),
    ("WF-SS", "Scrutiny + SAC/SHC", ["Scrutiny", "SAC/SHC"], 22),
]
POSTS = {"Scrutiny": 10, "EVC": 18, "SAC/SHC": 14, "Approval": 7, "Approved": 0, "Returned": 14}
DISTRIBUTION = [
    ("Scrutiny", 38), ("EVC", 27), ("SAC/SHC", 19),
    ("Approval", 18), ("Approved", 36), ("Returned", 12),
]
OWNERS = {
    "Scrutiny": ["Aditi Rao", "Vivek Shetty", "Nandita Bose"],
    "EVC": ["Arjun Menon"],
    "SAC/SHC": ["Prof. S. Nair", "Dr. Latha Menon"],
    "Approval": ["Dr. Meera Krishnan", "K. Ramanathan"],
    "Approved": ["Dr. Meera Krishnan"],
    "Returned": ["Institution nodal officer"],
}
USERS = [
    ("Dr. Meera Krishnan", "meera.krishnan@aicte.gov.in", "Bureau Officer", "All"),
    ("K. Ramanathan", "ramanathan.k@aicte.gov.in", "Regional Officer", "South"),
    ("Aditi Rao", "aditi.rao@aicte.gov.in", "Scrutiny Officer", "South"),
    ("Arjun Menon", "arjun.menon@aicte.gov.in", "EVC Coordinator", "South"),
    ("Prof. S. Nair", "s.nair@aicte.gov.in", "Committee Member (SAC/SHC)", "South"),
    ("Dr. Rohan Deshpande", "principal@vidyanagara.edu.in", "Institution", "South"),
    ("Neha Sharma", "neha.sharma@aicte.gov.in", "System Administrator", "All"),
]


def iso(days: int = 0) -> str:
    return (TODAY + timedelta(days=days)).isoformat()


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS regions;
        DROP TABLE IF EXISTS institutions;
        DROP TABLE IF EXISTS workflow_routes;
        DROP TABLE IF EXISTS applications;
        DROP TABLE IF EXISTS movements;
        DROP TABLE IF EXISTS evc_sessions;
        DROP TABLE IF EXISTS undertakings;
        DROP TABLE IF EXISTS documents;
        DROP TABLE IF EXISTS audit_events;

        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL, scope TEXT NOT NULL
        );
        CREATE TABLE regions (code TEXT PRIMARY KEY, name TEXT NOT NULL, officer TEXT NOT NULL);
        CREATE TABLE institutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE,
            name TEXT NOT NULL, city TEXT NOT NULL, region TEXT NOT NULL,
            type TEXT NOT NULL, new_institution INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE workflow_routes (
            code TEXT PRIMARY KEY, name TEXT NOT NULL, stages TEXT NOT NULL,
            target_days INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE applications (
            id TEXT PRIMARY KEY, institution_id INTEGER NOT NULL,
            institution_name TEXT NOT NULL, region TEXT NOT NULL,
            type TEXT NOT NULL, stage TEXT NOT NULL, status TEXT NOT NULL,
            route_code TEXT NOT NULL, route_name TEXT NOT NULL,
            days_in_stage INTEGER NOT NULL, sla_days INTEGER NOT NULL,
            owner TEXT NOT NULL, committee TEXT, submitted_on TEXT NOT NULL,
            return_reason TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, application_id TEXT NOT NULL,
            created_at TEXT NOT NULL, actor TEXT NOT NULL, role TEXT NOT NULL,
            action TEXT NOT NULL, note TEXT, FOREIGN KEY(application_id) REFERENCES applications(id)
        );
        CREATE TABLE evc_sessions (
            id TEXT PRIMARY KEY, application_id TEXT NOT NULL,
            institution_id INTEGER NOT NULL, institution_name TEXT NOT NULL,
            committee TEXT NOT NULL, visit_date TEXT NOT NULL, visit_time TEXT NOT NULL,
            mode TEXT NOT NULL, status TEXT NOT NULL, new_institution INTEGER NOT NULL
        );
        CREATE TABLE undertakings (
            id TEXT PRIMARY KEY, institution_id INTEGER NOT NULL,
            institution_name TEXT NOT NULL, category TEXT NOT NULL,
            condition TEXT NOT NULL, due_date TEXT NOT NULL, status TEXT NOT NULL,
            evidence_required INTEGER NOT NULL DEFAULT 1,
            verified_by TEXT, verified_on TEXT
        );
        CREATE TABLE documents (
            id TEXT PRIMARY KEY, institution_id INTEGER NOT NULL,
            institution_name TEXT NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL,
            issue_date TEXT NOT NULL, expiry_date TEXT NOT NULL,
            status TEXT NOT NULL, alert_window TEXT NOT NULL
        );
        CREATE TABLE audit_events (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, actor TEXT NOT NULL,
            actor_role TEXT NOT NULL, event_type TEXT NOT NULL, action TEXT NOT NULL,
            entity TEXT NOT NULL, detail TEXT NOT NULL,
            previous_hash TEXT NOT NULL, content_hash TEXT NOT NULL
        );
        """
    )


def seed() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    create_schema(connection)

    connection.executemany("INSERT INTO regions VALUES (?, ?, ?)", [(c, n, o) for n, (c, o) in REGIONS.items()])
    password_hash = generate_password_hash("AICTE@2026")
    connection.executemany(
        "INSERT INTO users (name, email, password_hash, role, scope) VALUES (?, ?, ?, ?, ?)",
        [(name, email, password_hash, role, scope) for name, email, role, scope in USERS],
    )

    for index, (name, city, region, inst_type) in enumerate(INSTITUTIONS, start=1):
        code = f"{REGIONS[region][0]}-{index:03d}"
        connection.execute(
            "INSERT INTO institutions (code, name, city, region, type, new_institution) VALUES (?, ?, ?, ?, ?, ?)",
            (code, name, city, region, inst_type, int(inst_type == "New institution")),
        )
    connection.executemany(
        "INSERT INTO workflow_routes VALUES (?, ?, ?, ?, 1)",
        [(code, name, json.dumps(stages), target) for code, name, stages, target in ROUTES],
    )

    days_by_stage = {
        "Scrutiny": [3, 5, 7, 9, 12, 18, 22, 31, 4, 6],
        "EVC": [5, 9, 12, 16, 19, 24, 27, 34, 41],
        "SAC/SHC": [4, 8, 11, 17, 21, 6],
        "Approval": [2, 4, 9, 12, 16, 3],
        "Approved": [0],
        "Returned": [4, 8, 11],
    }
    committees = ["EVC/04", "EVC/07", "EVC/11", "EVC/15"]
    serial = 1041
    for stage, count in DISTRIBUTION:
        for offset in range(count):
            institution_id = ((serial * 7) % 40) + 1
            name, city, region, inst_type = INSTITUTIONS[institution_id - 1]
            route = ROUTES[(serial + offset) % len(ROUTES)]
            if stage in ("EVC", "SAC/SHC"):
                route = next(item for item in ROUTES if stage in item[2])
            days = days_by_stage[stage][offset % len(days_by_stage[stage])]
            if stage != "Approved" and serial % 19 == 0:
                days = POSTS[stage] + 5
            status = "Approved" if stage == "Approved" else "Deficiency returned" if stage == "Returned" else "SLA breached" if days > POSTS[stage] else "Nearing SLA" if days >= POSTS[stage] * 0.75 else "On track"
            application_id = f"AICTE/{REGIONS[region][0]}/2026/{serial:05d}"
            connection.execute(
                """INSERT INTO applications VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    application_id, institution_id, name, region, inst_type, stage, status,
                    route[0], route[1], days, POSTS[stage], OWNERS[stage][offset % len(OWNERS[stage])],
                    committees[offset % 4], iso(-(21 + days)), "Evidence incomplete." if stage == "Returned" else None,
                    datetime_now(),
                ),
            )
            connection.execute(
                "INSERT INTO movements (application_id, created_at, actor, role, action, note) VALUES (?, ?, ?, ?, ?, ?)",
                (application_id, iso(-(21 + days)), "Institution portal", "Institution", "Application submitted", f"Submitted under {route[1]}."),
            )
            connection.execute(
                "INSERT INTO movements (application_id, created_at, actor, role, action, note) VALUES (?, ?, ?, ?, ?, ?)",
                (application_id, iso(-min(days, 20)), "Workflow engine", "Automation", f"Pending {stage}", "Movement requires an authorised manual action."),
            )
            serial += 1

    evc_cases = connection.execute(
        "SELECT id, institution_id, institution_name FROM applications WHERE stage = 'EVC' LIMIT 8"
    ).fetchall()
    for index, case in enumerate(evc_cases):
        connection.execute(
            "INSERT INTO evc_sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"EVC/2026/{51 + index:03d}", case[0], case[1], case[2], committees[index % 4],
             iso(index - 2), ["10:00", "11:30", "14:30"][index % 3],
             "Physical visit" if index % 2 == 0 else "Video conference",
             "Completed" if index < 2 else "Scheduled",
             int(INSTITUTIONS[(case[1] - 1) % 40][3] == "New institution")),
        )

    conditions = [
        ("Infrastructure", "Submit revised library catalogue and journal subscription invoices."),
        ("Statutory clearance", "Renew the fire-safety NOC and upload the renewed certificate."),
        ("Faculty", "Appoint two full-time faculty members in the Department of Computer Science."),
        ("Safety", "Submit a structural stability certificate for the new academic block."),
        ("Infrastructure", "Complete separate hostel accommodation for 120 women students."),
        ("Academic", "Submit audited evidence of the faculty-to-student ratio."),
    ]
    undertaking_offsets = [-21, -9, -4, 3, 7, 16, 29, 45, 68, 88, 120, 155, 180, 210, 250, 300, 15, 60]
    for index, offset in enumerate(undertaking_offsets):
        institution_id = (index * 3) % 40 + 1
        name, _, _, _ = INSTITUTIONS[institution_id - 1]
        category, condition = conditions[index % len(conditions)]
        status = "Overdue" if offset < 0 else "Evidence submitted" if index % 4 == 0 else "Pending"
        connection.execute(
            "INSERT INTO undertakings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"UT/2026/{101 + index:04d}", institution_id, name, category, condition, iso(offset), status, 1, None, None),
        )

    document_types = [
        ("Registered lease deed", "Land & premises"),
        ("Fire safety certificate", "Statutory clearance"),
        ("AICTE extension approval", "Approval record"),
        ("Building completion certificate", "Land & premises"),
        ("Land ownership title", "Land & premises"),
        ("Pollution control consent", "Statutory clearance"),
    ]
    for index, offset in enumerate([-46, -12, -3, 6, 18, 31, 57, 64, 86, 91, 122, 178, 24, 9, 43, 205, 156, 78, 29, 112, -7, 63, 14, 240]):
        institution_id = (index * 3) % 40 + 1
        name, _, _, _ = INSTITUTIONS[institution_id - 1]
        document, category = document_types[index % len(document_types)]
        status = "Expired" if offset < 0 else "Critical" if offset <= 7 else "Action required" if offset <= 30 else "Monitor" if offset <= 90 else "Valid"
        window = "Escalated" if offset < 0 else "7-day alert" if offset <= 7 else "30-day alert" if offset <= 30 else "60-day alert" if offset <= 60 else "90-day alert" if offset <= 90 else "Valid"
        connection.execute(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"DOC/2026/{301 + index:04d}", institution_id, name, document, category, iso(offset - 365), iso(offset), status, window),
        )

    previous = "GENESIS-2026-AICTE"
    events = [
        ("System — APScheduler", "Automation", "alert", "Daily alert scan executed", "JOB-DAILY-01", "Scanned the complete scoped register."),
        ("Aditi Rao", "Scrutiny Officer", "return", "Application returned for deficiency", "AICTE/SOU/2026/01175", "Land lease evidence was illegible."),
        ("Institution portal", "Institution", "submission", "Compliance evidence uploaded", "UT/2026/0101", "Evidence submitted for officer verification."),
        ("Workflow engine", "Automation", "workflow", "Stage automatically advanced", "AICTE/SOU/2026/01194", "Scrutiny completed manually; moved to EVC."),
        ("Dr. Meera Krishnan", "Bureau Officer", "decision", "Final approval recorded", "AICTE/NOR/2026/01346", "Approved subject to recorded undertakings."),
        ("System — Audit service", "Automation", "verify", "Audit hash chain verified", "AUDIT-CHAIN", "All predecessor and content hashes matched."),
    ]
    for index, (actor, role, event_type, action, entity, detail) in enumerate(events):
        record = {
            "ts": iso(-(len(events) - index)),
            "actor": actor,
            "eventType": event_type,
            "action": action,
            "entity": entity,
            "detail": detail,
        }
        content_hash = hashlib.sha256(
            f"{previous}|{json.dumps(record, sort_keys=True)}".encode()
        ).hexdigest()
        connection.execute(
            "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"AUD-{index + 1:05d}", datetime_now(index), actor, role, event_type, action, entity, detail, previous, content_hash),
        )
        previous = content_hash

    connection.commit()
    print(f"Seeded {DB_PATH}")
    print(f"  institutions: {len(INSTITUTIONS)}")
    print(f"  applications: {sum(count for _, count in DISTRIBUTION)}")
    print(f"  routes: {len(ROUTES)} · undertakings: {len(undertaking_offsets)} · documents: 24 · audit events: {len(events)}")
    print("Demo password: AICTE@2026")
    connection.close()


def datetime_now(offset_hours: int = 0) -> str:
    from datetime import datetime, timedelta
    return (datetime.now() - timedelta(hours=offset_hours)).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    seed()
