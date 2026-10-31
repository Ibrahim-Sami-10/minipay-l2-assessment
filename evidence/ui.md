# UI Test Evidence

The Playwright suite was run against the local Docker Compose deployment with
the configured API key:

```text
pytest -q tests/ui
5 passed, 1 warning in 3.16s
```

The warning is a pytest deprecation warning about a session-scoped fixture
defined as an instance method; it does not affect the completed test result.
The suite covers invalid-key login, successful login, transaction search,
not-found search, and successful payment submission.

## CI guidance

Run the health check, API smoke tests, and these UI journeys on every release.
Run the complete browser suite plus the larger SQL/Kubernetes regression
workflow on scheduled or pre-release builds. CI should start Compose with
test-only credentials, wait for `/health`, and publish the Playwright report
and screenshots as build artifacts.
