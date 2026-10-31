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
