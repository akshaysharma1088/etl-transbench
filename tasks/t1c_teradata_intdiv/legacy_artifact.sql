-- Legacy warehouse SQL (Teradata-style). Engine: Teradata 15.
-- Semantics notes: INTEGER / INTEGER performs integer division that TRUNCATES
-- TOWARD ZERO (so -150/100 = -1, not -2); ZEROIFNULL maps NULL to 0 BEFORE
-- the division; final CAST(... AS INTEGER) also truncates toward zero.
SELECT
    account_id,
    ZEROIFNULL(balance_cents) / 100                    AS balance_bucket,
    CAST(ZEROIFNULL(balance_cents) * fx_rate / 100 AS INTEGER) AS fx_units
FROM acct_balance
WHERE acct_type <> 'CLOSED'
