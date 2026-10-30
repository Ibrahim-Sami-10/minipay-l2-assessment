-- 7. Average and p95 processing time (in seconds) for completed transactions
SELECT
    status,
    COUNT(*) AS completed_transactions,
    ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)))::numeric, 2)
        AS average_processing_seconds,
    ROUND(
        percentile_cont(0.95) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (completed_at - created_at))
        )::numeric, 2
    ) AS p95_processing_seconds
FROM transactions
WHERE completed_at IS NOT NULL
GROUP BY status
ORDER BY status;
