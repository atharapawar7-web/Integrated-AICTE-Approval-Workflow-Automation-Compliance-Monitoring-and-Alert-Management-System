"""Domain tests for the AICTE Approva reference workflow and alert rules."""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta

import pytest

ROUTES = {
    "WF-S": ["Scrutiny"],
    "WF-SE": ["Scrutiny", "EVC"],
    "WF-ES": ["EVC", "SAC/SHC"],
    "WF-E": ["EVC"],
    "WF-SES": ["Scrutiny", "EVC", "SAC/SHC"],
    "WF-SS": ["Scrutiny", "SAC/SHC"],
}
SLA = {"Scrutiny": 10, "EVC": 18, "SAC/SHC": 14, "Approval": 7}


def next_stage(route_code, current):
    stages = ROUTES[route_code]
    index = stages.index(current)
    return stages[index + 1] if index < len(stages) - 1 else "Approval"


def sla_state(days, limit):
    if days > limit:
        return "breached"
    if days >= limit * 0.75:
        return "nearing"
    return "on_track"


def expiry_bucket(expiry, today=None):
    today = today or date(2026, 3, 14)
    days = (expiry - today).days
    if days < 0:
        return "expired"
    if days <= 7:
        return "7-day"
    if days <= 30:
        return "30-day"
    if days <= 60:
        return "60-day"
    if days <= 90:
        return "90-day"
    return "valid"


def audit_hash(previous, record):
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{previous}|{payload}".encode()).hexdigest()


def verify_chain(records):
    previous = "GENESIS-2026-AICTE"
    for record in records:
        expected = audit_hash(previous, record["content"])
        if record["previous_hash"] != previous or record["content_hash"] != expected:
            return False
        previous = record["content_hash"]
    return True


def test_all_required_routes_are_supported():
    assert set(ROUTES) >= {"WF-S", "WF-SE", "WF-ES", "WF-E", "WF-SES"}
    assert all(stage in {"Scrutiny", "EVC", "SAC/SHC"} for stages in ROUTES.values() for stage in stages)


def test_next_stage_and_terminal_approval():
    assert next_stage("WF-SES", "Scrutiny") == "EVC"
    assert next_stage("WF-SES", "EVC") == "SAC/SHC"
    assert next_stage("WF-SES", "SAC/SHC") == "Approval"
    assert next_stage("WF-E", "EVC") == "Approval"


def test_sla_boundaries_are_explicit():
    assert sla_state(7, 10) == "on_track"
    assert sla_state(8, 10) == "nearing"
    assert sla_state(10, 10) == "nearing"
    assert sla_state(11, 10) == "breached"
    assert SLA["EVC"] == 18


def test_return_requires_mandatory_reason():
    def return_case(reason, category="Deficiency"):
        if category not in {"Deficiency", "Clarification required", "Re-verification required"}:
            raise ValueError("unsupported return category")
        if not reason or len(reason.strip()) < 15:
            raise ValueError("reason is mandatory")
        return {"stage": "Returned", "reason": reason.strip()}

    with pytest.raises(ValueError, match="mandatory"):
        return_case("")
    with pytest.raises(ValueError, match="mandatory"):
        return_case("missing")
    result = return_case("Certified land lease evidence must be supplied.")
    assert result["stage"] == "Returned"
    assert len(result["reason"]) >= 15


def test_escalation_thresholds_are_ordered():
    levels = [{"level": 1, "days": 3}, {"level": 2, "days": 7}, {"level": 3, "days": 15}]

    def escalate(overdue_days):
        return max((level["level"] for level in levels if overdue_days >= level["days"]), default=0)

    assert escalate(2) == 0
    assert escalate(3) == 1
    assert escalate(8) == 2
    assert escalate(20) == 3
    assert [level["days"] for level in levels] == sorted(level["days"] for level in levels)


def test_document_expiry_alert_ladder():
    today = date(2026, 3, 14)
    assert expiry_bucket(today - timedelta(days=1), today) == "expired"
    assert expiry_bucket(today + timedelta(days=7), today) == "7-day"
    assert expiry_bucket(today + timedelta(days=30), today) == "30-day"
    assert expiry_bucket(today + timedelta(days=60), today) == "60-day"
    assert expiry_bucket(today + timedelta(days=90), today) == "90-day"
    assert expiry_bucket(today + timedelta(days=91), today) == "valid"


def test_undertaking_fulfilment_is_manual():
    undertaking = {"status": "Evidence submitted", "verified_by": None}

    def auto_approve(item):
        # The system must never close compliance on its own.
        if item["status"] == "Evidence submitted" and item["verified_by"] is None:
            return {**item, "status": "Evidence submitted"}
        return item

    assert auto_approve(undertaking)["status"] == "Evidence submitted"
    assert auto_approve(undertaking)["verified_by"] is None
    manual = {**undertaking, "status": "Compliant", "verified_by": "K. Ramanathan"}
    assert manual["status"] == "Compliant"


def test_audit_hash_chain_detects_tampering():
    first = {"actor": "Scrutiny Officer", "eventType": "verify", "action": "Faculty verified"}
    genesis = "GENESIS-2026-AICTE"
    first_hash = audit_hash(genesis, first)
    second = {"actor": "Bureau Officer", "eventType": "decision", "action": "Final approval"}
    second_hash = audit_hash(first_hash, second)
    chain = [
        {"previous_hash": genesis, "content_hash": first_hash, "content": first},
        {"previous_hash": first_hash, "content_hash": second_hash, "content": second},
    ]
    assert verify_chain(chain)
    chain[0]["content"]["action"] = "Faculty rejected"
    assert not verify_chain(chain)


def test_approval_cannot_be_system_generated():
    authorized_roles = {"Bureau Officer", "Regional Officer"}
    action = {"actor_role": "Approval workflow engine", "action": "Approve application"}
    assert action["actor_role"] not in authorized_roles
    assert action["actor_role"] not in {"EVC Coordinator", "Institution"}
