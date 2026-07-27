"""Verification for new T4 tasks: oracle self-check + planted classic-migration bugs."""
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

for tid in ["t4b_delete_reinsert", "t4c_stale_snapshot", "t4d_union_dedup_precedence"]:
    task = Task.load(os.path.join(ROOT, "tasks", tid))
    res = verify_candidate(task, task.reference)
    assert res.equivalent, f"{tid}: oracle self-verification FAILED: {res.reports or res.error}"
    print(f"PASS  {tid}: oracle self-verifies")

# t4b bug: upsert/merge instead of partition delete (ghost products survive)
bug_b = '''
import pandas as pd
def run(inputs):
    prior = inputs["target_snapshot_prior"]
    inbound = inputs["inbound"]
    stg = (inbound[inbound["qty"] > 0]
           .groupby(["product_id", "batch_date"], as_index=False)
           .agg(total_qty=("qty", "sum"), max_unit_cost=("unit_cost", "max")))
    # WRONG: keyed upsert -- prior rows for refreshed dates whose product is
    # absent today survive as ghosts
    keys = stg[["product_id", "batch_date"]].apply(tuple, axis=1)
    pk = prior[["product_id", "batch_date"]].apply(tuple, axis=1)
    kept = prior[~pk.isin(set(keys))]
    out = pd.concat([kept, stg], ignore_index=True)
    return {"target_snapshot": out[["product_id", "batch_date", "total_qty", "max_unit_cost"]]}
'''
check("t4b_delete_reinsert", bug_b, False, "t4b: upsert vs partition-delete (ghost rows) -> caught")

# t4c bug: delta computed against POST-update snapshot (all zeros)
bug_c = '''
import pandas as pd
def run(inputs):
    feed = inputs["score_feed"]
    curr = feed.groupby("account_id", as_index=False).agg(avg_score=("score", "mean"))
    snap = curr.copy()                                   # Step 3 applied first
    delta = curr.merge(snap.rename(columns={"avg_score": "old_avg"}), on="account_id", how="left")
    delta["score_delta"] = delta["avg_score"] - delta["old_avg"].fillna(0.0)
    return {"delta": delta[["account_id", "score_delta"]],
            "score_snapshot": curr[["account_id", "avg_score"]]}
'''
check("t4c_stale_snapshot", bug_c, False, "t4c: delta vs post-update snapshot -> caught")

# t4d bug: recency-first dedup (newest wins regardless of source)
bug_d = '''
import pandas as pd
def run(inputs):
    crm = inputs["crm_feed"].copy(); crm["src_rank"] = 1
    web = inputs["web_feed"].copy(); web["src_rank"] = 2
    both = pd.concat([crm, web], ignore_index=True)
    both = both.sort_values(["customer_id", "updated_at", "src_rank", "email"],
                            ascending=[True, False, True, True])   # WRONG order
    golden = both.drop_duplicates("customer_id", keep="first")
    return {"golden": golden[["customer_id", "email", "updated_at"]]}
'''
check("t4d_union_dedup_precedence", bug_d, False, "t4d: recency beats source precedence -> caught")

# t4d bug B: nondeterministic tie handling (email tiebreak dropped)
bug_d2 = '''
import pandas as pd
def run(inputs):
    crm = inputs["crm_feed"].copy(); crm["src_rank"] = 1
    web = inputs["web_feed"].copy(); web["src_rank"] = 2
    both = pd.concat([crm, web], ignore_index=True)
    both = both.sort_values(["customer_id", "src_rank", "updated_at"],
                            ascending=[True, True, False])          # no email ASC
    golden = both.drop_duplicates("customer_id", keep="first")
    return {"golden": golden[["customer_id", "email", "updated_at"]]}
'''
check("t4d_union_dedup_precedence", bug_d2, False, "t4d: missing email tiebreak -> caught")

print("\nALL NEW T4 TASKS VERIFIED (3 oracles, 4 bug probes)")
