
# SQL Performance Investigation

## Objective

Evaluate the performance of three common transaction investigation queries before and after adding database indexes.

The tests were conducted against the PostgreSQL database containing 50,000 transactions.

## Methodology

1. Drop the three test indexes.
2. Run ANALYZE on the transactions table.
3. Execute the queries using EXPLAIN (ANALYZE, BUFFERS).
4. Save the execution plans in `perf-output/before.txt`.
5. Create the indexes.
6. Run ANALYZE again.
7. Execute the same queries and save the results in `perf-output/after.txt`.

## Indexes Created

| Index | Purpose |
|---|---|
| idx_transactions_ref | Transaction reference lookups |
| idx_transactions_customer_created | Customer transaction history ordered by newest first |
| idx_transactions_processing | Searches for PROCESSING transactions |

The third index is a partial index and only includes rows where status = 'PROCESSING'.

## Actual Results

| Query | Before (ms) | After (ms) | Approx. improvement |
|---|---:|---:|---:|
| Transaction reference lookup | 4.324 | 0.114 | 37.9x |
| Customer transaction history | 2.858 | 0.413 | 6.9x |
| Stuck transaction search | 4.747 | 0.344 | 13.8x |

## Execution Plan Observations

### Before indexing

PostgreSQL used Sequential Scans (`Seq Scan`) for all three queries.

The transaction reference lookup examined 50,000 rows and removed 49,999 rows through filtering.

### After indexing

PostgreSQL used the following indexes:

- `idx_transactions_ref`
- `idx_transactions_customer_created`
- `idx_transactions_processing`

All three execution times decreased in this test.

## Evidence

- `perf-output/before.txt` contains the actual execution plans before indexing.
- `perf-output/after.txt` contains the actual execution plans after indexing.

## Conclusion

The three indexes improved the measured execution times for the tested queries.

The results demonstrate how appropriate indexing can reduce unnecessary table scans and improve database investigation performance.

These measurements represent this local PostgreSQL environment and 50,000-row dataset. Results may vary with different data volumes, hardware and database workloads.
