"""Verification for new T2 tasks: oracle self-check + planted classic-migration bugs."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from etl_transbench.harness import Task, verify_candidate, compile_candidate

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

def check(tid, code, expect_eq, label):
    task = Task.load(os.path.join(ROOT, "tasks", tid))
    fn, err = compile_candidate(code)
    assert fn, f"{label}: compile failed: {err}"
    res = verify_candidate(task, fn)
    assert res.equivalent == expect_eq, (
        f"{label}: expected equivalent={expect_eq}, got {res.equivalent}; "
        f"report={res.reports[-1] if res.reports else res.error}")
    print(f"PASS  {label}")

for tid in ["t2b_stmt_cycle_reset", "t2c_locf_carry_forward", "t2d_reject_skip_accum"]:
    task = Task.load(os.path.join(ROOT, "tasks", tid))
    res = verify_candidate(task, task.reference)
    assert res.equivalent, f"{tid}: oracle self-verification FAILED: {res.reports or res.error}"
    print(f"PASS  {tid}: oracle self-verifies")

# t2b bug: reset applied AFTER adding the STMT amount (fee lands in old cycle)
bug_b = '''
import pandas as pd
def run(inputs):
    df = inputs["ledger"].sort_values(["account_id", "entry_date", "row_seq"]).copy()
    is_stmt = (df["entry_type"] == "STMT").astype(int)
    # WRONG: cycle increments on the row AFTER the STMT row (shift), so the
    # statement fee posts into the OLD cycle
    df["cycle_no"] = 1 + is_stmt.groupby(df["account_id"]).cumsum().groupby(df["account_id"]).shift(1).fillna(0).astype(int)
    df["cycle_balance"] = (df["amount"].fillna(0)
                           .groupby([df["account_id"], df["cycle_no"]]).cumsum())
    return {"cycle_balances": df[["account_id", "row_seq", "entry_date",
                                  "entry_type", "amount", "cycle_no", "cycle_balance"]]}
'''
check("t2b_stmt_cycle_reset", bug_b, False, "t2b: reset-after-add (fee in old cycle) -> caught")

# t2c bug: global ffill leaks rates across account boundaries
bug_c = '''
import pandas as pd
def run(inputs):
    df = inputs["rate_feed"].sort_values(["account_id", "obs_date", "obs_seq"]).copy()
    filled = df["rate"].ffill()                      # WRONG: no groupby(account)
    df["was_carried"] = (df["rate"].isna() & filled.notna()).astype(int)
    df["rate_filled"] = filled
    return {"rate_filled": df[["account_id", "obs_seq", "obs_date",
                               "rate_filled", "was_carried"]]}
'''
check("t2c_locf_carry_forward", bug_c, False, "t2c: cross-account LOCF leak -> caught")

# t2d bug A: invalid rows included in the running total (posted as NaN/zero)
bug_d1 = '''
import pandas as pd
def run(inputs):
    df = inputs["postings"].sort_values(["account_id", "post_date", "post_seq"]).copy()
    df["post_value"] = df["qty"] * df["unit_price"]
    df["running_total"] = df.groupby("account_id")["post_value"].cumsum()  # WRONG: rejects not skipped
    bad = (df["qty"].isna() | (df["qty"] <= 0) | df["unit_price"].isna() | (df["unit_price"] < 0))
    good = df[~bad]
    rejects = bad.groupby(df["account_id"]).sum().astype(int).rename("reject_count").reset_index()
    return {"posted_totals": good[["account_id", "post_seq", "post_date", "post_value", "running_total"]],
            "reject_counts": rejects}
'''
check("t2d_reject_skip_accum", bug_d1, False, "t2d: rejects included in accumulator -> caught")

# t2d bug B: zero-reject accounts missing from REJECT_COUNTS
bug_d2 = '''
import pandas as pd
def run(inputs):
    df = inputs["postings"].sort_values(["account_id", "post_date", "post_seq"]).copy()
    bad = (df["qty"].isna() | (df["qty"] <= 0) | df["unit_price"].isna() | (df["unit_price"] < 0))
    good = df[~bad].copy()
    good["post_value"] = good["qty"] * good["unit_price"]
    good["running_total"] = good.groupby("account_id")["post_value"].cumsum()
    rejects = (df[bad].groupby("account_id").size().astype(int)  # WRONG: only accounts WITH rejects
               .rename("reject_count").reset_index())
    return {"posted_totals": good[["account_id", "post_seq", "post_date", "post_value", "running_total"]],
            "reject_counts": rejects}
'''
check("t2d_reject_skip_accum", bug_d2, False, "t2d: zero-reject accounts dropped -> caught")

print("\nALL NEW T2 TASKS VERIFIED (3 oracles, 4 bug probes)")
