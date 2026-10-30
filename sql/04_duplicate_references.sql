-- 4. Duplicate transaction references
SELECT
    transaction_ref,
    COUNT(*) AS duplicate_count,
    array_agg(id ORDER BY id) AS transaction_ids,
    array_agg(status ORDER BY id) AS statuses,
    SUM(amount) AS total_amount
FROM transactions
GROUP BY transaction_ref
HAVING COUNT(*) > 1
ORDER BY transaction_ref;
