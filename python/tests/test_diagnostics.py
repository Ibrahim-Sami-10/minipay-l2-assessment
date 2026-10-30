from datetime import datetime, timedelta
import pytest
from diagnostics import diagnose, normalize_reference

NOW = datetime(2026, 10, 30, 12, 0, 0)


def payment(**over):
    base = {
        "id": 1, "transaction_ref": "TXN00000001", "customer_id": 5, "amount": "10.00",
        "status": "SUCCESS", "created_at": "2026-10-30T11:00:00",
        "completed_at": "2026-10-30T11:00:30", "failure_code": None,
        "callbacks": [{"attempt_no": 1, "http_status": 200, "callback_status": "SUCCESS",
                       "attempted_at": "2026-10-30T11:00:35"}]
    }
    base.update(over)
    return base


def codes(result):
    return {a["code"] for a in result["anomalies"]}


@pytest.mark.parametrize("raw,expected", [
    ("TXN000123", "TXN00000123"),
    ("txn123", "TXN00000123"),
    ("TXN00000123", "TXN00000123"),
    (" TXN5 ", "TXN00000005"),
    ("12345", "12345"),
])
def test_normalize_reference(raw, expected):
    assert normalize_reference(raw) == expected


def test_healthy_success_has_no_anomalies():
    r = diagnose(payment(), NOW)
    assert r["anomalies"] == []
    assert r["recommended_action"] == "No action required."


def test_processing_over_15_minutes_is_stuck():
    created = (NOW - timedelta(minutes=16)).isoformat()
    r = diagnose(payment(status="PROCESSING", created_at=created, completed_at=None, callbacks=[]), NOW)
    assert "STUCK_PROCESSING" in codes(r)


def test_processing_under_15_minutes_not_stuck():
    created = (NOW - timedelta(minutes=5)).isoformat()
    r = diagnose(payment(status="PROCESSING", created_at=created, completed_at=None, callbacks=[]), NOW)
    assert "STUCK_PROCESSING" not in codes(r)


def test_failed_transaction_anomalies():
    r = diagnose(payment(status="FAILED", failure_code="UPSTREAM_ERROR", callbacks=[]), NOW)
    assert "PAYMENT_FAILED" in codes(r)


def test_success_with_failed_callbacks():
    cbs = [{"attempt_no": 1, "http_status": 503, "callback_status": "FAILED", "attempted_at": "..."}]
    r = diagnose(payment(callbacks=cbs), NOW)
    assert "CALLBACK_NOT_ACKNOWLEDGED" in codes(r)


def test_duplicate_reference_flagged():
    r = diagnose(payment(duplicate_reference=True, duplicate_ids=[4999, 5000]), NOW)
    assert "DUPLICATE_REFERENCE" in codes(r)
