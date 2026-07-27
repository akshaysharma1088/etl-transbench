-- Legacy warehouse SQL (T-SQL / SQL Server-style). Engine: SQL Server 2016.
-- Semantics notes: TOP (5) WITH TIES returns MORE than 5 rows when scores tie
-- at the cutoff rank; ISNULL coalesces; '+' string concat PROPAGATES NULL
-- (NULL + anything = NULL), unlike CONCAT.
SELECT TOP (5) WITH TIES
    branch_id,
    ISNULL(manager, 'UNASSIGNED')          AS manager_norm,
    branch_code + '-' + region_code        AS branch_label,
    score
FROM branch_scores
WHERE active = 1
ORDER BY score DESC
