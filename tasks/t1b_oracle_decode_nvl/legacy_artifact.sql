-- Legacy warehouse SQL (Oracle-style). Engine: Oracle 11g.
-- Semantics notes: DECODE treats NULL = NULL as a MATCH (unlike CASE equality);
-- NVL coalesces; TRUNC(ts,'MM') buckets to month start.
SELECT
    TRUNC(txn_ts, 'MM')                                   AS txn_month,
    DECODE(region, NULL, 'MISSING', 'XX', 'UNKNOWN', region) AS region_norm,
    SUM(NVL(amount, 0))                                   AS total_amount,
    COUNT(*)                                              AS txn_count
FROM regional_txn
WHERE status = 'POSTED'
GROUP BY TRUNC(txn_ts, 'MM'),
         DECODE(region, NULL, 'MISSING', 'XX', 'UNKNOWN', region)
