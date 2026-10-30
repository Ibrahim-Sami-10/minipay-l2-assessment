# INCIDENT-003 – Transaction Search Performance

**Priority:** P2  
**Reported by:** Operations  
**Status:** Resolved

---

## 1. Incident Summary & Observations
Operations reported that transaction searches and support investigations become progressively slower as data volume grows[cite: 53]. The benchmark was conducted against PostgreSQL 16 loaded with the 50,000-row synthetic dataset (1,000 customers, 50,000 transactions, and 56,589 callbacks)[cite: 53].

---

## 2. Evidence Gathered (Before Fix)
Inspection of `database/schema.sql` revealed no secondary indexes on the `transactions` table[cite: 30, 53]. Benchmarking with `EXPLAIN (ANALYZE, BUFFERS)` in `sql/perf-output/before.txt` showed full table sequential scans across all 616 heap pages[cite: 53]:
- Reference lookup (`TXN00031234`): Full table `Seq Scan` in **4.324 ms** (filtered out 49,999 rows)[cite: 53].
- Customer history (`customer_id = 436`): `Seq Scan` + in-memory quicksort in **2.858 ms**[cite: 53].
- Stuck sweep (`PROCESSING > 15 min`): `Seq Scan` + top-N heapsort in **4.747 ms** (filtered out 47,557 rows)[cite: 53].

At 50,000 rows cached in memory, queries take ~4 ms[cite: 53]. However, linear scans ($O(N)$) under concurrent read traffic and larger production volumes cause severe I/O contention and multi-second latencies[cite: 53].

---

## 3. Root Cause
The `transactions` table lacked secondary indexes for its primary lookup keys (`transaction_ref`, `(customer_id, created_at DESC)`, and active `PROCESSING` records), forcing PostgreSQL to execute full sequential scans and memory sorts on every query[cite: 53].

---

## 4. Corrective Action (`sql/indexes.sql`)
Created three targeted indexes tailored to the access patterns[cite: 53]:
1. `idx_transactions_ref`: Non-unique B-tree index on `transaction_ref` (kept non-unique because duplicate references exist legitimately in the dataset)[cite: 53].
2. `idx_transactions_customer_created`: Composite B-tree index on `(customer_id, created_at DESC)` eliminating the sort step[cite: 53].
3. `idx_transactions_processing`: Partial B-tree index on `(created_at) WHERE status = 'PROCESSING'` covering only ~4.9% of rows[cite: 53].

---

## 5. Validation After Fix (`sql/perf-output/after.txt`)
- Reference lookup: `4.324 ms` $\rightarrow$ **`0.114 ms`** (37.9x faster, buffer reads reduced from 616 to 3)[cite: 53].
- Customer history: `2.858 ms` $\rightarrow$ **`0.413 ms`** (6.9x faster, sort eliminated)[cite: 53].
- Stuck sweep: `4.747 ms` $\rightarrow$ **`0.344 ms`** (13.8x faster, sort eliminated)[cite: 53].

---

## 6. Preventive Controls
- Use `CREATE INDEX CONCURRENTLY` in production to prevent write locks on the transactions table.
- Enforce `EXPLAIN (ANALYZE, BUFFERS)` validation in pull request reviews for queries touching unindexed columns.
- Configure `pg_stat_statements` and alert when statement durations exceed 250 ms.
