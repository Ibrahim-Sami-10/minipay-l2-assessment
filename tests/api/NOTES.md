# API Test Notes

- **Timeouts:** clients should use bounded connect/read timeouts and treat a
  timeout as indeterminate until the payment is queried by its idempotency key.
- **Retries:** retry only safe GET requests automatically. Payment POST retries
  must reuse the same `Idempotency-Key`; never create a new key for a retry.
- **Idempotency:** the API stores a request hash and rejects reuse of a key
  with a different request body using HTTP 409.
- **4xx vs 5xx:** 4xx responses identify client validation, authentication,
  or resource errors and should be corrected or surfaced. 5xx responses are
  server/dependency failures and may be retried according to the integration's
  bounded retry policy.
