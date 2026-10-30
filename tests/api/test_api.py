"""Comprehensive API integration test suite for MiniPay."""
import uuid
import pytest
import requests


# ---------------------------------------------------------------------------
# 1. Health Endpoints
# ---------------------------------------------------------------------------
def test_health_live(base_url):
    resp = requests.get(f"{base_url}/health/live", timeout=5)
    assert resp.status_code == 200
    assert resp.json().get("status") == "alive"


def test_health_with_database(base_url):
    resp = requests.get(f"{base_url}/health", timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"
    assert data.get("database") == "up"


# ---------------------------------------------------------------------------
# 2. Authentication & Authorization
# ---------------------------------------------------------------------------
def test_unauthorized_when_missing_api_key(base_url):
    resp = requests.get(f"{base_url}/api/payments", timeout=5)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_unauthorized_when_invalid_api_key(base_url):
    headers = {"X-API-Key": "completely-invalid-key"}
    resp = requests.get(f"{base_url}/api/payments", headers=headers, timeout=5)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


# ---------------------------------------------------------------------------
# 3. Customer Endpoints
# ---------------------------------------------------------------------------
def test_create_and_get_customer(base_url, auth_headers):
    unique_ref = f"CUST_TEST_{uuid.uuid4().hex[:8]}"
    payload = {"customer_ref": unique_ref, "name": "Integration Test Customer"}
    
    # Create customer
    post_resp = requests.post(f"{base_url}/api/customers", json=payload, headers=auth_headers, timeout=5)
    assert post_resp.status_code == 201
    data = post_resp.json()
    assert data["customer_ref"] == unique_ref
    assert data["name"] == "Integration Test Customer"
    cust_id = data["id"]
    
    # Fetch by ID
    get_resp = requests.get(f"{base_url}/api/customers/{cust_id}", headers=auth_headers, timeout=5)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == cust_id


def test_create_duplicate_customer_fails(base_url, auth_headers):
    unique_ref = f"CUST_DUP_{uuid.uuid4().hex[:8]}"
    payload = {"customer_ref": unique_ref, "name": "Duplicate Test"}
    
    r1 = requests.post(f"{base_url}/api/customers", json=payload, headers=auth_headers, timeout=5)
    assert r1.status_code == 201
    
    r2 = requests.post(f"{base_url}/api/customers", json=payload, headers=auth_headers, timeout=5)
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "duplicate_customer"


def test_get_nonexistent_customer(base_url, auth_headers):
    resp = requests.get(f"{base_url}/api/customers/9999999", headers=auth_headers, timeout=5)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "customer_not_found"


# ---------------------------------------------------------------------------
# 4. Payment Creation & Idempotency
# ---------------------------------------------------------------------------
def test_create_payment_success(base_url, auth_headers, unique_idempotency_key):
    headers = dict(auth_headers)
    headers["Idempotency-Key"] = unique_idempotency_key
    payload = {"customer_id": 1, "amount": 150.50}

    resp = requests.post(f"{base_url}/api/payments", json=payload, headers=headers, timeout=5)
    assert resp.status_code == 201
    data = resp.json()
    assert data["customer_id"] == 1
    assert data["amount"] == "150.50"
    assert data["status"] == "SUCCESS"
    assert "transaction_ref" in data
    assert len(data.get("callbacks", [])) >= 1


def test_create_payment_missing_idempotency_key(base_url, auth_headers):
    payload = {"customer_id": 1, "amount": 50.00}
    resp = requests.post(f"{base_url}/api/payments", json=payload, headers=auth_headers, timeout=5)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "missing_idempotency_key"


def test_create_payment_nonexistent_customer(base_url, auth_headers, unique_idempotency_key):
    headers = dict(auth_headers)
    headers["Idempotency-Key"] = unique_idempotency_key
    payload = {"customer_id": 9999999, "amount": 50.00}

    resp = requests.post(f"{base_url}/api/payments", json=payload, headers=headers, timeout=5)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "customer_not_found"


def test_idempotent_replay_returns_cached_payment(base_url, auth_headers, unique_idempotency_key):
    headers = dict(auth_headers)
    headers["Idempotency-Key"] = unique_idempotency_key
    payload = {"customer_id": 1, "amount": 75.25}

    # First attempt: Created (201)
    r1 = requests.post(f"{base_url}/api/payments", json=payload, headers=headers, timeout=5)
    assert r1.status_code == 201
    data1 = r1.json()

    # Replay attempt: 200 OK with Idempotent-Replayed header
    r2 = requests.post(f"{base_url}/api/payments", json=payload, headers=headers, timeout=5)
    assert r2.status_code == 200
    assert r2.headers.get("Idempotent-Replayed") == "true"
    data2 = r2.json()
    assert data1["id"] == data2["id"]
    assert data1["transaction_ref"] == data2["transaction_ref"]


def test_idempotency_key_reuse_with_different_body_conflicts(base_url, auth_headers, unique_idempotency_key):
    headers = dict(auth_headers)
    headers["Idempotency-Key"] = unique_idempotency_key

    # Initial request
    r1 = requests.post(f"{base_url}/api/payments", json={"customer_id": 1, "amount": 25.00}, headers=headers, timeout=5)
    assert r1.status_code == 201

    # Conflict request: same key, different amount
    r2 = requests.post(f"{base_url}/api/payments", json={"customer_id": 1, "amount": 99.00}, headers=headers, timeout=5)
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "idempotency_key_reuse"


# ---------------------------------------------------------------------------
# 5. Lookups & INCIDENT-001 Regression Verification
# ---------------------------------------------------------------------------
def test_get_payment_by_numeric_id(base_url, auth_headers):
    resp = requests.get(f"{base_url}/api/payments/123", headers=auth_headers, timeout=5)
    assert resp.status_code == 200
    assert resp.json()["id"] == 123


def test_get_payment_by_unique_reference(base_url, auth_headers):
    resp = requests.get(f"{base_url}/api/payments/TXN00000123", headers=auth_headers, timeout=5)
    assert resp.status_code == 200
    assert resp.json()["transaction_ref"] == "TXN00000123"


def test_duplicate_reference_does_not_return_500(base_url, auth_headers):
    """Regression test for INCIDENT-001."""
    resp = requests.get(f"{base_url}/api/payments/TXN00004999", headers=auth_headers, timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data["transaction_ref"] == "TXN00004999"
    assert data.get("duplicate_reference") is True
    assert data.get("duplicate_ids") == [4999, 5000]


def test_get_nonexistent_payment(base_url, auth_headers):
    resp = requests.get(f"{base_url}/api/payments/TXN99999999", headers=auth_headers, timeout=5)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "payment_not_found"


# ---------------------------------------------------------------------------
# 6. Customer Payment History & Query Filters
# ---------------------------------------------------------------------------
def test_customer_payment_history(base_url, auth_headers):
    resp = requests.get(f"{base_url}/api/customers/436/payments?limit=10", headers=auth_headers, timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data["customer_id"] == 436
    assert len(data["payments"]) <= 10
    # Check descending order by created_at
    dates = [p["created_at"] for p in data["payments"]]
    assert dates == sorted(dates, reverse=True)


def test_list_payments_by_status(base_url, auth_headers):
    resp = requests.get(f"{base_url}/api/payments?status=PROCESSING&limit=5", headers=auth_headers, timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert all(p["status"] == "PROCESSING" for p in data["payments"])