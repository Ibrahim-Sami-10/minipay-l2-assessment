"""Playwright UI automation tests for MiniPay dashboard."""
import os
import pytest
from playwright.sync_api import Page, expect

BASE_URL = os.environ.get("MINIPAY_API_URL", "http://localhost:8080").rstrip("/")
API_KEY = os.environ.get("MINIPAY_API_KEY") or os.environ.get("API_KEY")


@pytest.fixture(autouse=True)
def check_api_key():
    if not API_KEY:
        pytest.fail(
            "MINIPAY_API_KEY or API_KEY is not set. Export it before running tests:\n"
            "  export MINIPAY_API_KEY=$(grep '^API_KEY=' .env | cut -d '=' -f2-)"
        )


def test_login_failure_with_invalid_key(page: Page):
    page.goto(BASE_URL)
    page.fill('[data-testid="api-key-input"]', "invalid-wrong-key")
    page.click('[data-testid="login-button"]')

    msg = page.locator('[data-testid="login-message"]')
    expect(msg).to_contain_text("Login failed: invalid API key")
    expect(page.locator('[data-testid="app-section"]')).to_be_hidden()


def test_login_success_reveals_app(page: Page):
    page.goto(BASE_URL)
    page.fill('[data-testid="api-key-input"]', API_KEY)
    page.click('[data-testid="login-button"]')

    expect(page.locator('[data-testid="login-section"]')).to_be_hidden()
    expect(page.locator('[data-testid="app-section"]')).to_be_visible()


def test_search_transaction_success(page: Page):
    page.goto(BASE_URL)
    page.fill('[data-testid="api-key-input"]', API_KEY)
    page.click('[data-testid="login-button"]')
    expect(page.locator('[data-testid="app-section"]')).to_be_visible()

    page.fill('[data-testid="search-input"]', "TXN00000123")
    page.click('[data-testid="search-button"]')

    msg = page.locator('[data-testid="search-message"]')
    expect(msg).to_contain_text("Found TXN00000123")
    result = page.locator('[data-testid="search-result"]')
    expect(result).to_be_visible()
    expect(result).to_contain_text("TXN00000123")


def test_search_transaction_not_found(page: Page):
    page.goto(BASE_URL)
    page.fill('[data-testid="api-key-input"]', API_KEY)
    page.click('[data-testid="login-button"]')
    expect(page.locator('[data-testid="app-section"]')).to_be_visible()

    page.fill('[data-testid="search-input"]', "TXN99999999")
    page.click('[data-testid="search-button"]')

    msg = page.locator('[data-testid="search-message"]')
    expect(msg).to_contain_text("Transaction not found")


def test_submit_payment_flow(page: Page):
    page.goto(BASE_URL)
    page.fill('[data-testid="api-key-input"]', API_KEY)
    page.click('[data-testid="login-button"]')
    expect(page.locator('[data-testid="app-section"]')).to_be_visible()

    page.fill('[data-testid="payment-customer-input"]', "1")
    page.fill('[data-testid="payment-amount-input"]', "125.00")
    page.click('[data-testid="payment-submit-button"]')

    msg = page.locator('[data-testid="payment-message"]')
    expect(msg).to_contain_text("SUCCESS")
    result = page.locator('[data-testid="payment-result"]')
    expect(result).to_be_visible()
    expect(result).to_contain_text('"status": "SUCCESS"')