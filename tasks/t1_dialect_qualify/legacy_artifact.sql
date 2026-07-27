-- Legacy warehouse SQL (Teradata-style). Engine: legacy MPP warehouse.
-- Semantics notes: QUALIFY filters on window results after computation.
SELECT
    account_id,
    txn_id,
    txn_ts,
    amount,
    channel,
    CASE WHEN amount >= 1000 THEN 'JUMBO'
         WHEN amount >= 500  THEN 'LARGE'
         ELSE 'STANDARD' END AS size_band
FROM acct_txn
WHERE amount > 100
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id
    ORDER BY txn_ts DESC, txn_id DESC
) = 1
