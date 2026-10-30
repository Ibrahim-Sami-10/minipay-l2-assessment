"""Thin, defensive HTTP client for the MiniPay API."""
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger("support_tool.client")


class NotFound(Exception):
    pass


class AuthError(Exception):
    pass


class ApiUnavailable(Exception):
    """Network failure, timeout, or 5xx from the API."""
    pass


class MiniPayClient:
    def __init__(self, base_url, api_key, timeout=10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key, "Accept": "application/json"})
        
        # Retry only idempotent GETs on transient 502/503/504 errors with exponential backoff.
        # Deterministic 500 errors are not retried to avoid amplifying load.
        retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[502, 503, 504],
                      allowed_methods=["GET"])
        self.session.mount("http://", HTTPAdapter(max_retries=retry))
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def _get(self, path, params=None):
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.get(url, params=params, timeout=(3, self.timeout))
        except requests.exceptions.RequestException as exc:
            raise ApiUnavailable(f"Cannot reach {url}: {exc.__class__.__name__}") from exc
        
        rid = resp.headers.get("X-Request-ID")
        log.debug("GET %s -> %s request_id=%s", url, resp.status_code, rid)
        
        if resp.status_code == 401:
            raise AuthError("API rejected the API key (HTTP 401)")
        if resp.status_code == 404:
            raise NotFound(path)
        if resp.status_code >= 500:
            raise ApiUnavailable(f"API error HTTP {resp.status_code} (request_id={rid})")
        
        resp.raise_for_status()
        return resp.json()

    def get_payment(self, ident):
        return self._get(f"/api/payments/{ident}")

    def list_payments(self, **params):
        return self._get("/api/payments", params=params)

    def health(self):
        """Returns (http_status, body). 503 is an informative answer here."""
        url = f"{self.base_url}/health"
        try:
            resp = self.session.get(url, timeout=(3, self.timeout))
        except requests.exceptions.RequestException as exc:
            raise ApiUnavailable(f"Cannot reach {url}: {exc.__class__.__name__}") from exc
        try:
            body = resp.json()
        except ValueError:
            body = {}
        return resp.status_code, body
