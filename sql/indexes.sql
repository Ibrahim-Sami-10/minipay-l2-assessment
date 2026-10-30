-- 1. Non-unique B-tree index for reference lookups (non-unique because duplicate refs exist)
CREATE INDEX IF NOT EXISTS idx_transactions_ref
    ON transactions (transaction_ref);

-- 2. Composite index for customer payment history sorted by newest first
CREATE INDEX IF NOT EXISTS idx_transactions_customer_created
    ON transactions (customer_id, created_at DESC);

-- 3. Partial index for stuck PROCESSING transactions sweep (~5% of rows)
CREATE INDEX IF NOT EXISTS idx_transactions_processing
    ON transactions (created_at)
    WHERE status = 'PROCESSING';

ANALYZE transactions;
