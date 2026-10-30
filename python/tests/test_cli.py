from unittest.mock import patch
import pytest
import support_tool
from minipay_client import ApiUnavailable, AuthError, NotFound

GOOD = {
    "id": 1, "transaction_ref": "TXN00000001", "customer_id": 5, "amount": "10.00",
    "status": "SUCCESS", "created_at": "2026-10-30T11:00:00", "completed_at": "2026-10-30T11:00:30",
    "failure_code": None, "callbacks": [{"attempt_no": 1, "http_status": 200, "callback_status": "SUCCESS"}]
}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("MINIPAY_API_KEY", "test-key")
    monkeypatch.delenv("MINIPAY_CONFIG", raising=False)


def run(argv):
    return support_tool.main(argv)


def test_ok_exit_code(capsys):
    with patch("support_tool.MiniPayClient.get_payment", return_value=GOOD):
        assert run(["--transaction", "TXN1"]) == support_tool.EXIT_OK
    out = capsys.readouterr().out
    assert "TXN00000001" in out


def test_not_found_exit_code(capsys):
    with patch("support_tool.MiniPayClient.get_payment", side_effect=NotFound("x")):
        assert run(["-t", "TXN9999"]) == support_tool.EXIT_NOT_FOUND


def test_api_unavailable_exit_code():
    with patch("support_tool.MiniPayClient.get_payment", side_effect=ApiUnavailable("boom")):
        assert run(["-t", "TXN1"]) == support_tool.EXIT_UNAVAILABLE


def test_auth_error_exit_code():
    with patch("support_tool.MiniPayClient.get_payment", side_effect=AuthError("401")):
        assert run(["-t", "TXN1"]) == support_tool.EXIT_CONFIG
