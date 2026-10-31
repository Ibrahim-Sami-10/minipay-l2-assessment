"""Shared fixtures for API integration tests."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("MINIPAY_API_URL", "http://localhost:8080").rstrip("/")
API_KEY = os.environ.get("MINIPAY_API_KEY") or os.environ.get("API_KEY")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def api_key():
    if not API_KEY:
        pytest.fail(
            "MINIPAY_API_KEY or API_KEY is not set. Export it before running pytest:\n"
            "  export MINIPAY_API_KEY=$(grep '^API_KEY=' .env | cut -d '=' -f2-)"
        )
    return API_KEY


@pytest.fixture
def auth_headers(api_key):
    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


@pytest.fixture
def unique_idempotency_key():
    return str(uuid.uuid4())