"""Verification for new T1 tasks: oracle self-check + planted classic-migration bugs."""
import os, sys
ROOT = os.path.dirname(os.path.abspath("etl_transbench"))
sys.path.insert(0, ".")
from etl_transbench.harness import Task, verify_candidate, compile_candidate

def check(tid, code, expect_eq, label):
    task = Task.load(os.path.join("tasks", tid))
    fn, err = compile_candidate(code)
    assert fn, f"{label}: compile failed: {err}"
    res = verify_candidate(task, fn)
    assert res.equivalent == expect_eq, (
        f"{label}: expected equivalent={expect_eq}, got {res.equivalent}; "
        f"report={res.reports[-1] if res.reports else res.error}")
    print(f"PASS  {label}")

# ---- 1. oracle self-verification ----
for tid in ["t1b_oracle_decode_nvl", "t1c_teradata_intdiv", "t1d_tsql_top_ties"]:
    task = Task.load(os.path.join("tasks", tid))
    res = verify_candidate(task, task.reference)
    assert res.equivalent, f"{tid}: oracle self-verification FAILED: {res.reports or res.error}"
    print(f"PASS  {tid}: oracle self-verifies")

# ---- 2. planted bugs ----
# t1b bug A: CASE-style equality (no NULL match) -> NULL regions leak as NaN group
bug_b1 = '''
import pandas as pd
def run(inputs):
    df = inputs["regional_txn"]
    df = df[df["status"] == "POSTED"].copy()
    df["txn_month"] = df["txn_ts"].dt.to_period("M").dt.to_timestamp()
    df["region_norm"] = df["region"].map(lambda r: "UNKNOWN" if r == "XX" else r)  # misses NULL->MISSING
    df["amount_nvl"] = df["amount"].fillna(0.0)
    out = (df.groupby(["txn_month", "region_norm"], as_index=False)
             .agg(total_amount=("amount_nvl", "sum"), txn_count=("amount_nvl", "size")))
    return {"monthly_region_rollup": out}
'''
check("t1b_oracle_decode_nvl", bug_b1, False, "t1b: DECODE null-match dropped -> caught")

# t1b bug B: COUNT(*) translated as count(amount) (drops null-amount rows)
bug_b2 = '''
import pandas as pd
def _dec(r):
    if pd.isna(r): return "MISSING"
    return "UNKNOWN" if r == "XX" else r
def run(inputs):
    df = inputs["regional_txn"]
    df = df[df["status"] == "POSTED"].copy()
    df["txn_month"] = df["txn_ts"].dt.to_period("M").dt.to_timestamp()
    df["region_norm"] = df["region"].apply(_dec)
    out = (df.groupby(["txn_month", "region_norm"], as_index=False)
             .agg(total_amount=("amount", "sum"), txn_count=("amount", "count")))  # count drops NULLs
    return {"monthly_region_rollup": out}
'''
check("t1b_oracle_decode_nvl", bug_b2, False, "t1b: COUNT(*) vs count(col) -> caught")

# t1c bug: floor division instead of trunc-toward-zero
bug_c = '''
def run(inputs):
    df = inputs["acct_balance"]
    df = df[df["acct_type"] != "CLOSED"].copy()
    cents = df["balance_cents"].fillna(0.0)
    df["balance_bucket"] = cents // 100          # floor: wrong on negatives
    df["fx_units"] = (cents * df["fx_rate"] / 100.0).astype("int64", errors="ignore")
    import numpy as np
    df["fx_units"] = np.floor(cents * df["fx_rate"] / 100.0)
    return {"balance_buckets": df[["account_id", "balance_bucket", "fx_units"]]}
'''
check("t1c_teradata_intdiv", bug_c, False, "t1c: floor vs trunc-toward-zero -> caught")

# t1d bug A: head(5) drops WITH TIES
bug_d1 = '''
import pandas as pd
def run(inputs):
    df = inputs["branch_scores"]
    df = df[df["active"] == 1].copy()
    df["manager_norm"] = df["manager"].fillna("UNASSIGNED")
    def _label(row):
        if pd.isna(row["branch_code"]) or pd.isna(row["region_code"]): return None
        return f'{row["branch_code"]}-{row["region_code"]}'
    df["branch_label"] = df.apply(_label, axis=1)
    out = df.sort_values("score", ascending=False).head(5)   # drops ties at rank 5
    return {"top_branches": out[["branch_id", "manager_norm", "branch_label", "score"]]}
'''
check("t1d_tsql_top_ties", bug_d1, False, "t1d: head(5) drops WITH TIES -> caught")

# t1d bug B: CONCAT-style label (empty for NULL) instead of NULL propagation
bug_d2 = '''
import pandas as pd
def run(inputs):
    df = inputs["branch_scores"]
    df = df[df["active"] == 1].copy()
    df["manager_norm"] = df["manager"].fillna("UNASSIGNED")
    df["branch_label"] = df["branch_code"].fillna("") + "-" + df["region_code"].fillna("")  # CONCAT semantics
    df["rk"] = df["score"].rank(method="min", ascending=False)
    out = df[df["rk"] <= 5][["branch_id", "manager_norm", "branch_label", "score"]]
    return {"top_branches": out}
'''
check("t1d_tsql_top_ties", bug_d2, False, "t1d: CONCAT vs NULL-propagating '+' -> caught")

print("\nALL NEW T1 TASKS VERIFIED (3 oracles, 5 bug probes)")
