# INCIDENT-001 – Intermittent Transaction Search Failure (HTTP 500)

**Priority:** P2  
**Reported by:** Client Operations  
**Status:** Resolved

---

## 1. Observations and Reproduction Steps
Client Operations reported that transaction searches intermittently return HTTP 500 errors, while other transaction IDs work as expected.

Testing against the live MiniPay REST API reproduced the issue deterministically based on the transaction reference:

```console
# A. Single non-duplicate reference -> 200 OK
$ curl -i -H "X-API-Key: $API_KEY" http://localhost:8080/api/payments/TXN00000123
HTTP/1.1 200 OK
X-Request-ID: 77215b593664
{"id":123,"transaction_ref":"TXN00000123","customer_id":503,"amount":"44872.64","status":"SUCCESS",...}

# B. Duplicate reference -> 500 Internal Server Error
$ curl -i -H "X-API-Key: $API_KEY" http://localhost:8080/api/payments/TXN00004999
HTTP/1.1 500 INTERNAL SERVER ERROR
X-Request-ID: 01c15a162aab
{"error":{"code":"internal_error","message":"Internal server error","request_id":"01c15a162aab"}}
