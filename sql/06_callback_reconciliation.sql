-- 6. Reconciliation: successful transaction count/value vs callback-success count/value
WITH successful_txns AS (
    SELECT
        t.id,
        t.amount,
        DATE(t.created_at) AS transaction_date,
        EXISTS (
            SELECT 1
            FROM callbacks cb
            WHERE cb.transaction_id = t.id
              AND cb.callback_status = 'SUCCESS'
        ) AS has_successful_callback
    FROM transactions t
    WHERE t.status = 'SUCCESS'
)
SELECT
    transaction_date,
    COUNT(*) AS successful_txn_count,
    SUM(amount) AS successful_txn_value,
    COUNT(*) FILTER (WHERE has_successful_callback) AS callback_success_count,
    SUM(amount) FILTER (WHERE has_successful_callback) AS callback_success_value,
    COUNT(*) FILTER (WHERE NOT has_successful_callback) AS missing_callback_count,
    SUM(amount) FILTER (WHERE NOT has_successful_callback) AS missing_callback_value
FROM successful_txns
GROUP BY ROLLUP (transaction_date)
ORDER BY transaction_date NULLS LAST;
