"""Verification for new T3 tasks: oracle self-check + planted classic-migration bugs."""
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

for tid in ["t3b_dup_lookup_first", "t3c_router_first_match", "t3d_dedup_null_group"]:
    task = Task.load(os.path.join(ROOT, "tasks", tid))
    res = verify_candidate(task, task.reference)
    assert res.equivalent, f"{tid}: oracle self-verification FAILED: {res.reports or res.error}"
    print(f"PASS  {tid}: oracle self-verifies")

# t3b bug: naive left merge on non-unique lookup -> row explosion + wrong rates
bug_b = '''
import pandas as pd
def run(inputs):
    s = inputs["shipments"]
    r = inputs["carrier_rates"][["carrier_id", "rate_per_kg", "service_tier"]]
    m = s.merge(r, on="carrier_id", how="left")           # WRONG: duplicates rows
    m["rate_per_kg"] = m["rate_per_kg"].fillna(0.0)
    m["service_tier"] = m["service_tier"].fillna("NONE")
    m["freight_cost"] = m["weight_kg"] * m["rate_per_kg"]
    return {"shipment_costs": m[["shipment_id", "carrier_id", "service_tier",
                                 "weight_kg", "rate_per_kg", "freight_cost"]]}
'''
check("t3b_dup_lookup_first", bug_b, False, "t3b: naive merge row-explosion -> caught")

# t3b bug 2: dedup by physical first row instead of first_by policy
bug_b2 = '''
import pandas as pd
def run(inputs):
    s = inputs["shipments"]
    r = inputs["carrier_rates"].drop_duplicates("carrier_id", keep="first")  # WRONG: physical order
    m = s.merge(r[["carrier_id", "rate_per_kg", "service_tier"]], on="carrier_id", how="left")
    m["rate_per_kg"] = m["rate_per_kg"].fillna(0.0)
    m["service_tier"] = m["service_tier"].fillna("NONE")
    m["freight_cost"] = m["weight_kg"] * m["rate_per_kg"]
    return {"shipment_costs": m[["shipment_id", "carrier_id", "service_tier",
                                 "weight_kg", "rate_per_kg", "freight_cost"]]}
'''
check("t3b_dup_lookup_first", bug_b2, False, "t3b: physical-first vs first_by policy -> caught")

# t3c bug: rules evaluated independently (row lands on multiple ports)
bug_c = '''
def run(inputs):
    df = inputs["claims"]
    cols = ["claim_id", "amount", "photos_attached"]
    ft = df[(df["amount"] <= 500) & (df["photos_attached"] == 1)]
    hv = df[df["amount"] > 10000]
    mr = df[(df["photos_attached"] == 0) | (df["amount"] > 500)]   # WRONG: overlaps hv
    return {"claims_fast_track": ft[cols], "claims_high_value": hv[cols],
            "claims_manual_review": mr[cols]}
'''
check("t3c_router_first_match", bug_c, False, "t3c: independent rules (multi-port rows) -> caught")

# t3d bug A: dedup keep="first" (earliest read instead of latest)
bug_d1 = '''
import pandas as pd
def run(inputs):
    df = inputs["meter_reads"].sort_values(["meter_id", "read_ts", "read_seq"]).copy()
    latest = df.drop_duplicates("meter_id", keep="first")             # WRONG
    out = (latest.groupby("zone", dropna=False, as_index=False)
                 .agg(total_kwh=("kwh", "sum"), meter_count=("kwh", "size")))
    return {"zone_totals": out[["zone", "total_kwh", "meter_count"]]}
'''
check("t3d_dedup_null_group", bug_d1, False, "t3d: keep-first vs keep-last -> caught")

# t3d bug B: groupby default drops NULL zone group
bug_d2 = '''
import pandas as pd
def run(inputs):
    df = inputs["meter_reads"].sort_values(["meter_id", "read_ts", "read_seq"]).copy()
    latest = df.drop_duplicates("meter_id", keep="last")
    out = (latest.groupby("zone", as_index=False)                     # WRONG: dropna default
                 .agg(total_kwh=("kwh", "sum"), meter_count=("kwh", "size")))
    return {"zone_totals": out[["zone", "total_kwh", "meter_count"]]}
'''
check("t3d_dedup_null_group", bug_d2, False, "t3d: NULL zone group dropped -> caught")

print("\nALL NEW T3 TASKS VERIFIED (3 oracles, 6 bug probes)")
