"""Verification for new T5 tasks: oracle self-check + planted classic-migration bugs."""
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

for tid in ["t5b_scd2_multi_batch", "t5c_scd1_scd2_mixed", "t5d_asof_reconstruction"]:
    task = Task.load(os.path.join(ROOT, "tasks", tid))
    res = verify_candidate(task, task.reference)
    assert res.equivalent, f"{tid}: oracle self-verification FAILED: {res.reports or res.error}"
    print(f"PASS  {tid}: oracle self-verifies")

# t5b bug: dedup-to-latest before applying (drops intermediate versions and A->B->A chains)
bug_b = '''
import pandas as pd
def _neq(a, b):
    an, bn = pd.isna(a), pd.isna(b)
    if an and bn: return False
    if an != bn: return True
    return a != b
def run(inputs):
    dim = inputs["dim_product"].copy()
    stg = (inputs["stg_product"].sort_values(["product_id", "update_date"])
           .groupby("product_id", as_index=False).tail(1))          # WRONG: dedup
    rows = dim.to_dict("records")
    for s in stg.to_dict("records"):
        cur_idx = next((i for i, r in enumerate(rows)
                        if r["product_id"] == s["product_id"] and r["is_current"] == 1), None)
        if cur_idx is None:
            rows.append(dict(product_id=s["product_id"], category=s["category"],
                             price_band=s["price_band"], eff_start_date=s["update_date"],
                             eff_end_date=pd.NaT, is_current=1))
        else:
            c = rows[cur_idx]
            if _neq(c["category"], s["category"]) or _neq(c["price_band"], s["price_band"]):
                c["eff_end_date"] = s["update_date"]; c["is_current"] = 0
                rows.append(dict(product_id=s["product_id"], category=s["category"],
                                 price_band=s["price_band"], eff_start_date=s["update_date"],
                                 eff_end_date=pd.NaT, is_current=1))
    out = pd.DataFrame(rows, columns=["product_id", "category", "price_band",
                                      "eff_start_date", "eff_end_date", "is_current"])
    return {"dim_product_out": out}
'''
check("t5b_scd2_multi_batch", bug_b, False, "t5b: dedup-to-latest drops version chain -> caught")

# t5c bug A: email change triggers a Type-2 version
bug_c1 = '''
import pandas as pd
def _neq(a, b):
    an, bn = pd.isna(a), pd.isna(b)
    if an and bn: return False
    if an != bn: return True
    return a != b
def run(inputs):
    dim = inputs["dim_acct"].copy()
    stg = (inputs["stg_acct"].sort_values(["acct_id", "update_date", "email", "tier"],
           ascending=[True, True, True, True], na_position="first")
           .groupby("acct_id", as_index=False).tail(1))
    rows = dim.to_dict("records")
    for s in stg.to_dict("records"):
        cur_idx = next((i for i, r in enumerate(rows)
                        if r["acct_id"] == s["acct_id"] and r["is_current"] == 1), None)
        if cur_idx is None:
            rows.append(dict(acct_id=s["acct_id"], email=s["email"], tier=s["tier"],
                             eff_start_date=s["update_date"], eff_end_date=pd.NaT, is_current=1))
            continue
        c = rows[cur_idx]
        if _neq(c["tier"], s["tier"]) or _neq(c["email"], s["email"]):   # WRONG: email versions
            c["eff_end_date"] = s["update_date"]; c["is_current"] = 0
            rows.append(dict(acct_id=s["acct_id"], email=s["email"], tier=s["tier"],
                             eff_start_date=s["update_date"], eff_end_date=pd.NaT, is_current=1))
    out = pd.DataFrame(rows, columns=["acct_id", "email", "tier",
                                      "eff_start_date", "eff_end_date", "is_current"])
    return {"dim_acct_out": out}
'''
check("t5c_scd1_scd2_mixed", bug_c1, False, "t5c: Type-2 versioning on email change -> caught")

# t5c bug B: Type-1 overwrite applied only to the current row (history keeps old email)
bug_c2 = '''
import pandas as pd
def _neq(a, b):
    an, bn = pd.isna(a), pd.isna(b)
    if an and bn: return False
    if an != bn: return True
    return a != b
def run(inputs):
    dim = inputs["dim_acct"].copy()
    stg = (inputs["stg_acct"].sort_values(["acct_id", "update_date", "email", "tier"],
           ascending=[True, True, True, True], na_position="first")
           .groupby("acct_id", as_index=False).tail(1))
    rows = dim.to_dict("records")
    for s in stg.to_dict("records"):
        cur_idx = next((i for i, r in enumerate(rows)
                        if r["acct_id"] == s["acct_id"] and r["is_current"] == 1), None)
        if cur_idx is None:
            rows.append(dict(acct_id=s["acct_id"], email=s["email"], tier=s["tier"],
                             eff_start_date=s["update_date"], eff_end_date=pd.NaT, is_current=1))
            continue
        c = rows[cur_idx]
        if _neq(c["tier"], s["tier"]):
            c["eff_end_date"] = s["update_date"]; c["is_current"] = 0
            rows.append(dict(acct_id=s["acct_id"], email=s["email"], tier=s["tier"],
                             eff_start_date=s["update_date"], eff_end_date=pd.NaT, is_current=1))
        if _neq(c["email"], s["email"]):
            for r in rows:
                if r["acct_id"] == s["acct_id"] and r["is_current"] == 1:  # WRONG: current only
                    r["email"] = s["email"]
    out = pd.DataFrame(rows, columns=["acct_id", "email", "tier",
                                      "eff_start_date", "eff_end_date", "is_current"])
    return {"dim_acct_out": out}
'''
check("t5c_scd1_scd2_mixed", bug_c2, False, "t5c: Type-1 overwrite skips history rows -> caught")

# t5d bug: end-INCLUSIVE interval (boundary dates match two versions)
bug_d = '''
import pandas as pd
def run(inputs):
    h = inputs["dim_emp_hist"]
    q = inputs["asof_queries"]
    m = q.merge(h, on="emp_id", how="inner")
    ok = (m["as_of_date"] >= m["eff_start_date"]) & (
        m["eff_end_date"].isna() | (m["as_of_date"] <= m["eff_end_date"]))   # WRONG: <=
    return {"asof_result": m[ok][["query_id", "emp_id", "dept", "grade"]]}
'''
check("t5d_asof_reconstruction", bug_d, False, "t5d: end-inclusive interval (dup matches) -> caught")

print("\nALL NEW T5 TASKS VERIFIED (3 oracles, 4 bug probes)")
