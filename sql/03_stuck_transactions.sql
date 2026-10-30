-- 3. Transactions that have remained in PROCESSING for more than 15 minutes
SELECT
    COUNT(*) AS stuck_count,
    MIN(created_at) AS oldest_created_at
FROM transactions
WHERE status = 'PROCESSING'
  AND created_at < CURRENT_TIMESTAMP - INTERVAL '15 minutes';

SELECT
    id,
    transaction_ref,
    customer_id,
    amount,
    created_at,
    CURRENT_TIMESTAMP - created_at AS time_in_processing
FROM transactions
WHERE status = 'PROCESSING'
  AND created_at < CURRENT_TIMESTAMP - INTERVAL '15 minutes'
ORDER BY created_at
LIMIT 50;
