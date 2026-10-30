-- 2. Top 10 customers by successful transaction value
SELECT
    c.id,
    c.customer_ref,
    c.name,
    COUNT(t.id) AS successful_transactions,
    SUM(t.amount) AS successful_value
FROM customers c
JOIN transactions t ON c.id = t.customer_id
WHERE t.status = 'SUCCESS'
GROUP BY c.id, c.customer_ref, c.name
ORDER BY successful_value DESC
LIMIT 10;
