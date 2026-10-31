# INCIDENT-001 – Transaction Search Failure for Duplicate References (HTTP 500)

**Priority:** P2
**Reported by:** Client Operations
**Status:** Resolved

---

## 1. Observations and Reproduction Steps

Client Operations reported that transaction searches return HTTP 500 errors. The report described the failures as intermittent. Testing showed they occur only for references that match more than one transaction, so the failure is deterministic for each affected reference.

The application did not produce this fault naturally. As the assessment brief permits, the defect was introduced deliberately in commit `cc4cad4`, where the `fetch_one_strict` helper is commented as a deliberate flaw. It was then fixed in commit `3aac20a`.

Reproduction on the defective build:

```console
# A. Unique reference -> 200 OK
$ curl -i -H "X-API-Key: $API_KEY" http://localhost:8080/api/payments/TXN00000123
HTTP/1.1 200 OK
X-Request-ID: 77215b593664

# B. Duplicate reference -> 500 Internal Server Error
$ curl -i -H "X-API-Key: $API_KEY" http://localhost:8080/api/payments/TXN00004999
HTTP/1.1 500 INTERNAL SERVER ERROR
X-Request-ID: 01c15a162aab
{"error":{"code":"internal_error","message":"Internal server error","request_id":"01c15a162aab"}}
```

## 2. Hypotheses

- **H1:** Duplicate `transaction_ref` values exist in the data. The schema has no unique constraint on `transaction_ref`, and `database/generate_data.py` creates duplicates on purpose. **Confirmed** by the SQL check in section 3.
- **H2:** The lookup code assumes one row per reference. **Confirmed** by reading the defective `fetch_one_strict` helper.
- **H3:** The database or connection failed. **Ruled out:** `/health` returned `database: up`, and unique-reference lookups returned 200 against the same database.

## 3. Evidence

- `sql/04_duplicate_references.sql` returns 10 duplicated references, from `TXN00004999` to `TXN00049999`, one every 5,000 IDs. Each has exactly two rows. Statuses vary, for example `TXN00004999` has one `FAILED` and one `SUCCESS` row.
- `database/generate_data.py` sets the reference to `i - 1` when `i % 5000 == 0`, so transaction 5000 reuses `TXN00004999`. This explains the pattern.
- The defective `get_payment` raised `RuntimeError` when `len(rows) > 1`. The global error handler then returned `500 internal_error`.

## 4. Root Cause

The `fetch_one_strict` helper, introduced in `cc4cad4`, raised a `RuntimeError` whenever a reference matched more than one row. The route did not handle the exception, so the global handler returned HTTP 500.

The root cause is an incorrect assumption that `transaction_ref` is unique. The schema and the data do not guarantee that.

## 5. Immediate Corrective Action

In `3aac20a`, `get_payment` returns the oldest matching record (`ORDER BY id`) instead of raising an error. When more than one row matches, the response includes `duplicate_reference: true` and `duplicate_ids`, and a warning is logged with the request ID.

## 6. Permanent Corrective and Preventive Actions

- The lookup no longer assumes uniqueness. Duplicate matches are an explicit, handled case.
- The regression test `test_duplicate_reference_does_not_return_500` in `tests/api/test_api.py` checks that `TXN00004999` returns 200 with the duplicate flag.
- Support staff can see duplicates in the response and in the logs, so they can investigate them.
- Recommended, not yet done: a monitoring alert on the duplicate-reference warning, and a decision on whether `transaction_ref` should become unique in future data. Adding that constraint now would need a migration, because existing data contains duplicates.

## 7. Validation

- `TXN00000123` returns `200 OK` (checked 2026-10-31 10:58).
- `TXN00004999` returns `200 OK` with `"duplicate_reference": true` and `"duplicate_ids": [4999, 5000]` (checked 2026-10-31 10:58).
- `GET /api/payments?limit=1` returns `200 OK` (checked 2026-10-31 11:08), after the line 336 SQL fix.
- `pytest tests/api -k duplicate_reference -v` passes: `1 passed, 17 deselected`.
