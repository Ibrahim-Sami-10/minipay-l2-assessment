-- Query A: Single transaction lookup by reference
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, transaction_ref, status, amount
FROM transactions
WHERE transaction_ref = 'TXN00031234';

-- Query B: Customer recent transactions history
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, transaction_ref, status, amount, created_at
FROM transactions
WHERE customer_id = 436
ORDER BY created_at DESC
LIMIT 50;

-- Query C: Stuck PROCESSING transactions sweep
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, transaction_ref, created_at
FROM transactions
WHERE status = 'PROCESSING'
  AND created_at < CURRENT_TIMESTAMP - INTERVAL '15 minutes'
ORDER BY created_at
LIMIT 50;
