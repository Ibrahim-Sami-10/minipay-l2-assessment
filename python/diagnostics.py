"""Pure diagnostic logic: evaluates payment payloads without network I/O.
Fully unit-testable without database or network dependencies.
"""
from datetime import datetime, timedelta

# Consistent 15-minute threshold matching requirements/02-sql.md & requirements/04-python.md
STUCK_AFTER = timedelta(minutes=15)
SLOW_AFTER_SECONDS = 100

FAILURE_CODES = {
    "UPSTREAM_ERROR": (
        "The upstream payment processor returned an error.",
        "Check processor status. The customer may retry with a new Idempotency-Key once upstream recovers."
    ),
    "AMOUNT_LIMIT_EXCEEDED": (
        "The amount exceeds the single-transaction limit.",
        "Advise the customer to reduce or split the transaction amount; no funds were debited."
    ),
}


def parse_ts(value):
    return datetime.fromisoformat(value) if value else None


def normalize_reference(text):
    """Normalizes references like TXN123 or TXN000123 into canonical TXN00000123."""
    text = text.strip()
    if text.upper().startswith("TXN") and text[3:].isdigit():
        return "TXN" + text[3:].zfill(8)
    return text


def finding(code, severity, message):
    return {"code": code, "severity": severity, "message": message}


def diagnose(payment, now=None):
    """Analyzes a payment dictionary and returns anomalies and recommended actions."""
    now = now or datetime.now()
    status = payment.get("status")
    created = parse_ts(payment.get("created_at"))
    completed = parse_ts(payment.get("completed_at"))
    callbacks = payment.get("callbacks") or []
    anomalies = []
    cause, action = None, None

    proc_seconds = (completed - created).total_seconds() if created and completed else None

    # Status-based checks
    if status == "PROCESSING":
        age = now - created if created else None
        if age is not None and age > STUCK_AFTER:
            mins = int(age.total_seconds() // 60)
            anomalies.append(finding(
                "STUCK_PROCESSING", "high",
                f"In PROCESSING for {mins} minutes (threshold is 15 minutes)."
            ))
            cause = "Transaction never received a completion callback or status update."
            action = "Check upstream gateway state before retrying to avoid double-charging, then escalate to L3."
        else:
            cause, action = "Transaction is currently within normal processing time.", "Re-check in 2 minutes."

    elif status == "FAILED":
        code = payment.get("failure_code")
        known = FAILURE_CODES.get(code)
        anomalies.append(finding("PAYMENT_FAILED", "medium", f"Payment failed with code {code}."))
        cause, action = known if known else (
            f"Failed with unrecognized failure code {code!r}.", "Escalate to L3 with transaction reference."
        )

    elif status == "SUCCESS":
        ok = [c for c in callbacks if c.get("callback_status") == "SUCCESS"]
        if not callbacks:
            anomalies.append(finding(
                "NO_CALLBACK_RECORDED", "high",
                "Payment succeeded but no callback notification was ever recorded."
            ))
            cause = "Merchant callback dispatcher was not triggered."
            action = "Trigger manual callback resend from operations dashboard."
        elif not ok:
            codes = sorted({str(c.get("http_status")) for c in callbacks})
            anomalies.append(finding(
                "CALLBACK_NOT_ACKNOWLEDGED", "high",
                f"Payment succeeded but all {len(callbacks)} callback attempt(s) failed (HTTP {', '.join(codes)})."
            ))
            cause = "Merchant callback listener failed or returned non-200 responses."
            action = "Notify merchant of endpoint failures and verify their listener before retrying callback."
        elif len(callbacks) > 1:
            anomalies.append(finding(
                "CALLBACK_RETRIED", "low",
                f"Callback required {len(callbacks)} attempts before succeeding."
            ))

    # Data integrity checks
    if status in ("SUCCESS", "FAILED") and completed is None:
        anomalies.append(finding("MISSING_COMPLETED_AT", "high", f"{status} transaction has null completed_at."))
    if status == "PROCESSING" and completed is not None:
        anomalies.append(finding("COMPLETED_WHILE_PROCESSING", "medium", "completed_at is set while status is PROCESSING."))
    if created and completed and completed < created:
        anomalies.append(finding("TIME_TRAVEL", "high", "completed_at timestamp is earlier than created_at."))
    if proc_seconds is not None and proc_seconds > SLOW_AFTER_SECONDS:
        anomalies.append(finding("SLOW_PROCESSING", "low", f"Processing took {proc_seconds:.0f}s (threshold 100s)."))
    if payment.get("duplicate_reference"):
        anomalies.append(finding(
            "DUPLICATE_REFERENCE", "medium",
            f"Reference is shared by IDs {payment.get('duplicate_ids')}; returning oldest record."
        ))

    if not anomalies:
        cause, action = "No anomalies detected.", "No action required."

    cause = cause or "See findings."
    action = action or "Review the findings above."
    return {
        "anomalies": anomalies,
        "likely_cause": cause,
        "recommended_action": action,
        "processing_seconds": proc_seconds,
    }
