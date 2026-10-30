-- 5. Daily transaction success rate as a percentage
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
