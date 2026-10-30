"""MiniPay - Payment REST API + UI for Implementation & L2 Assessment.

Configuration via environment variables:
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD -> PostgreSQL connection
  API_KEY                                         -> sent by clients in X-API-Key
"""
import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from decimal import Decimal, InvalidOperation

import psycopg2
import psycopg2.extras
from flask import Flask, g, jsonify, request

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("minipay")

app = Flask(__name__, static_folder="static", static_url_path="/static")

MAX_AMOUNT = Decimal("10000000.00")
LIMIT_AMOUNT = Decimal("500000.00")  # amounts above this simulate processor decline


# --------------------------------------------------------------------------
# Database Helpers
# --------------------------------------------------------------------------
def cfg(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable {name}")
    return value


def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(
            host=cfg("DB_HOST", "localhost"),
            port=int(cfg("DB_PORT", "5432")),
            dbname=cfg("DB_NAME", "minipay"),
            user=cfg("DB_USER", "minipay"),
            password=cfg("DB_PASSWORD", ""),
            connect_timeout=3,
            options="-c statement_timeout=10000",
        )
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, params=()):
    with get_db().cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


# --------------------------------------------------------------------------
# Response Helpers
# --------------------------------------------------------------------------
def error(status, code, message, **extra):
    body = {"error": {"code": code, "message": message, "request_id": g.get("request_id")}}
    body["error"].update(extra)
    return jsonify(body), status


def serialise(row):
    out = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            out[k] = f"{v:.2f}"
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


# --------------------------------------------------------------------------
# Middleware: Request ID, Authentication, Access Logging
# --------------------------------------------------------------------------
@app.before_request
def before():
    g.start = time.time()
    g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    if request.path.startswith("/api/"):
        supplied = request.headers.get("X-API-Key", "")
        expected = cfg("API_KEY", "")
        if not expected or not hmac.compare_digest(supplied, expected):
            return error(401, "unauthorized", "Missing or invalid X-API-Key header")


@app.after_request
def after(resp):
    ms = (time.time() - g.get("start", time.time())) * 1000
    resp.headers["X-Request-ID"] = g.get("request_id", "-")
    log.info("req_id=%s %s %s -> %s %.1fms", g.get("request_id"), request.method,
             request.path, resp.status_code, ms)
    return resp


@app.errorhandler(404)
def not_found(_e):
    return error(404, "not_found", "Resource not found")


@app.errorhandler(405)
def method_not_allowed(_e):
    return error(405, "method_not_allowed", "Method not allowed")


@app.errorhandler(Exception)
def unhandled(exc):
    log.exception("req_id=%s unhandled error: %s", g.get("request_id"), exc)
    return error(500, "internal_error", "Internal server error")


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


# --------------------------------------------------------------------------
# Health & Static UI
# --------------------------------------------------------------------------
@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/health/live")
def live():
    return jsonify(status="alive")


@app.get("/health")
def health():
    try:
        query("SELECT 1 AS ok")
        return jsonify(status="ok", database="up")
    except Exception as exc:
        log.error("health check failed: %s", exc)
        return jsonify(status="degraded", database="down"), 503


# --------------------------------------------------------------------------
# Customers
# --------------------------------------------------------------------------
REF_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


@app.post("/api/customers")
def create_customer():
    body = json_body()
    if body is None:
        return error(400, "invalid_json", "Request body must be a JSON object")
    ref, name = body.get("customer_ref"), body.get("name")
    problems = {}
    if not isinstance(ref, str) or not REF_RE.match(ref):
        problems["customer_ref"] = "required, 1-40 chars: letters, digits, _ or -"
    if not isinstance(name, str) or not (1 <= len(name.strip()) <= 120):
        problems["name"] = "required, 1-120 characters"
    if problems:
        return error(400, "validation_error", "Invalid request", fields=problems)

    db = get_db()
    try:
        with db.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO customers(customer_ref, name) VALUES (%s, %s) "
                "RETURNING id, customer_ref, name, created_at",
                (ref, name.strip()),
            )
            row = cur.fetchone()
        db.commit()
    except psycopg2.errors.UniqueViolation:
        db.rollback()
        return error(409, "duplicate_customer", f"customer_ref {ref} already exists")
    resp = jsonify(serialise(row))
    resp.status_code = 201
    resp.headers["Location"] = f"/api/customers/{row['id']}"
    return resp


@app.get("/api/customers/<int:customer_id>")
def get_customer(customer_id):
    rows = query("SELECT id, customer_ref, name, created_at FROM customers WHERE id=%s",
                 (customer_id,))
    if not rows:
        return error(404, "customer_not_found", f"Customer {customer_id} not found")
    return jsonify(serialise(rows[0]))


@app.get("/api/customers/<int:customer_id>/payments")
def customer_payments(customer_id):
    if not query("SELECT 1 FROM customers WHERE id=%s", (customer_id,)):
        return error(404, "customer_not_found", f"Customer {customer_id} not found")
    try:
        limit = min(max(int(request.args.get("limit", 50)), 1), 200)
    except ValueError:
        return error(400, "validation_error", "limit must be an integer")
    rows = query(
        "SELECT id, transaction_ref, customer_id, amount, status, created_at, "
        "completed_at, failure_code FROM transactions "
        "WHERE customer_id=%s ORDER BY created_at DESC LIMIT %s",
        (customer_id, limit),
    )
    return jsonify(customer_id=customer_id, count=len(rows),
                   payments=[serialise(r) for r in rows])


# --------------------------------------------------------------------------
# Payments
# --------------------------------------------------------------------------
def payment_with_callbacks(row):
    callbacks = query(
        "SELECT attempt_no, http_status, callback_status, attempted_at "
        "FROM callbacks WHERE transaction_id=%s ORDER BY attempt_no",
        (row["id"],),
    )
    out = serialise(row)
    out["callbacks"] = [serialise(c) for c in callbacks]
    return out


PAYMENT_COLS = ("id, transaction_ref, customer_id, amount, status, created_at, "
                "completed_at, failure_code")


@app.post("/api/payments")
def create_payment():
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key or len(key) > 100:
        return error(400, "missing_idempotency_key",
                     "Idempotency-Key header is required (max 100 chars)")
    body = json_body()
    if body is None:
        return error(400, "invalid_json", "Request body must be a JSON object")

    customer_id, raw_amount = body.get("customer_id"), body.get("amount")
    problems = {}
    if not isinstance(customer_id, int) or isinstance(customer_id, bool) or customer_id < 1:
        problems["customer_id"] = "required positive integer"
    amount = None
    try:
        if isinstance(raw_amount, bool) or raw_amount is None:
            raise InvalidOperation
        amount = Decimal(str(raw_amount))
        if not (Decimal("0") < amount <= MAX_AMOUNT) or amount != amount.quantize(Decimal("0.01")):
            raise InvalidOperation
    except InvalidOperation:
        problems["amount"] = "required number > 0, at most 2 decimals, max 10000000.00"
    if problems:
        return error(400, "validation_error", "Invalid request", fields=problems)

    req_hash = hashlib.sha256(
        json.dumps({"customer_id": customer_id, "amount": f"{amount:.2f}"}, sort_keys=True).encode()
    ).hexdigest()

    db = get_db()
    try:
        with db.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT 1 FROM customers WHERE id=%s", (customer_id,))
            if cur.fetchone() is None:
                db.rollback()
                return error(422, "customer_not_found", f"Customer {customer_id} does not exist")

            cur.execute(
                "INSERT INTO idempotency_keys(key, request_hash) VALUES (%s, %s) "
                "ON CONFLICT (key) DO NOTHING RETURNING key", (key, req_hash))
            claimed = cur.fetchone() is not None

            if not claimed:
                cur.execute("SELECT request_hash, transaction_id FROM idempotency_keys WHERE key=%s", (key,))
                prev = cur.fetchone()
                db.rollback()
                if prev["request_hash"] != req_hash:
                    return error(409, "idempotency_key_reuse",
                                 "Idempotency-Key was already used with a different request body")
                rows = query(f"SELECT {PAYMENT_COLS} FROM transactions WHERE id=%s",
                             (prev["transaction_id"],))
                resp = jsonify(payment_with_callbacks(rows[0]))
                resp.headers["Idempotent-Replayed"] = "true"
                return resp

            cur.execute("SELECT nextval(pg_get_serial_sequence('transactions','id')) AS id")
            new_id = cur.fetchone()["id"]
            ref = f"TXN{new_id:08d}"
            ok = amount <= LIMIT_AMOUNT
            cur.execute(
                "INSERT INTO transactions(id, transaction_ref, customer_id, amount, status, "
                "created_at, completed_at, failure_code) "
                "VALUES (%s,%s,%s,%s,%s,now(),now(),%s)",
                (new_id, ref, customer_id, amount,
                 "SUCCESS" if ok else "FAILED", None if ok else "AMOUNT_LIMIT_EXCEEDED"))
            if ok:
                cur.execute(
                    "INSERT INTO callbacks(transaction_id, attempt_no, http_status, "
                    "callback_status, attempted_at) VALUES (%s,1,200,'SUCCESS',now())", (new_id,))
            cur.execute("UPDATE idempotency_keys SET transaction_id=%s WHERE key=%s", (new_id, key))
        db.commit()
    except psycopg2.Error:
        db.rollback()
        raise

    rows = query(f"SELECT {PAYMENT_COLS} FROM transactions WHERE id=%s", (new_id,))
    resp = jsonify(payment_with_callbacks(rows[0]))
    resp.status_code = 201
    resp.headers["Location"] = f"/api/payments/{new_id}"
    return resp


@app.get("/api/payments")
def list_payments():
    status = request.args.get("status")
    if status and status not in ("PROCESSING", "SUCCESS", "FAILED"):
        return error(400, "validation_error", "status must be PROCESSING, SUCCESS or FAILED")
    try:
        older = request.args.get("older_than_minutes")
        older = int(older) if older is not None else None
        limit = min(max(int(request.args.get("limit", 50)), 1), 500)
    except ValueError:
        return error(400, "validation_error", "older_than_minutes and limit must be integers")
    sql, params = f"SELECT {PAYMENT_COLS} FROM transactions WHERE TRUE", []
    if status:
        sql += " AND status=%s"
        params.append(status)
    if older is not None:
        sql += " AND created_at < now() - (%s * interval '1 minute')"
        params.append(older)
    sql += " ORDER BY created_at ASC LIMIT %s"
    params.append(limit)
    rows = query(sql, tuple(params))
    return jsonify(count=len(rows), payments=[serialise(r) for r in rows])


@app.get("/api/payments/<ident>")
def get_payment(ident):
    """ident is either the numeric id (e.g. 123) or a transaction_ref (e.g. TXN00000123).

    transaction_ref is NOT unique in the database (imported data contains duplicates).
    We return the oldest match, flag the duplicate status, and log a warning.
    """
    if ident.isdigit():
        rows = query(f"SELECT {PAYMENT_COLS} FROM transactions WHERE id=%s", (int(ident),))
    else:
        rows = query(f"SELECT {PAYMENT_COLS} FROM transactions WHERE transaction_ref=%s ORDER BY id", (ident,))

    if not rows:
        return error(404, "payment_not_found", f"Payment {ident} not found")

    out = payment_with_callbacks(rows[0])
    if len(rows) > 1:
        out["duplicate_reference"] = True
        out["duplicate_ids"] = [r["id"] for r in rows]
        log.warning("req_id=%s duplicate transaction_ref=%s ids=%s",
                    g.get("request_id"), ident, out["duplicate_ids"])

    return jsonify(out)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(cfg("PORT", "8080")))