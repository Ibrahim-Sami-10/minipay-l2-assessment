-- 1. Transaction counts by day and status
SELECT
    DATE(created_at) AS transaction_date,
    status,
    COUNT(*) AS total
FROM transactions
GROUP BY DATE(created_at), status
ORDER BY transaction_date, status;


-- 2. Top 10 customers by transaction volume
SELECT
    c.customer_ref,
    c.name,
    COUNT(t.id) AS transaction_count
FROM customers c
JOIN transactions t ON c.id = t.customer_id
GROUP BY c.id, c.customer_ref, c.name
ORDER BY transaction_count DESC
LIMIT 10;


-- 3. Transactions stuck in PROCESSING for more than 30 minutes
SELECT
    id,
    transaction_ref,
    customer_id,
    amount,
    created_at
FROM transactions
WHERE status = 'PROCESSING'
  AND created_at < CURRENT_TIMESTAMP - INTERVAL '30 minutes'
ORDER BY created_at;


-- 4. Duplicate transaction references
SELECT
    transaction_ref,
    COUNT(*) AS duplicate_count
FROM transactions
GROUP BY transaction_ref
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;


-- 5. Daily transaction success rate
SELECT
    DATE(created_at) AS transaction_date,
    COUNT(*) AS total_transactions,
    COUNT(*) FILTER (WHERE status = 'SUCCESS') AS successful_transactions,
    ROUND(
        COUNT(*) FILTER (WHERE status = 'SUCCESS') * 100.0
        / NULLIF(COUNT(*), 0), 2
    ) AS success_rate_percent
FROM transactions
GROUP BY DATE(created_at)
ORDER BY transaction_date;


-- 6. Transaction and callback reconciliation
SELECT
    t.status AS transaction_status,
    cb.callback_status,
    COUNT(DISTINCT t.id) AS transaction_count
FROM transactions t
LEFT JOIN callbacks cb ON t.id = cb.transaction_id
GROUP BY t.status, cb.callback_status
ORDER BY t.status, cb.callback_status;


-- 7. Average transaction processing time by status (completed only)
SELECT
    status,
    COUNT(*) AS completed_transactions,
    ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - created_at))), 2)
        AS average_processing_seconds
FROM transactions
WHERE completed_at IS NOT NULL
GROUP BY status
ORDER BY status;
