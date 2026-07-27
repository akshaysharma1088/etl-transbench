"""Full-benchmark tests: all 8 category exemplars + targeted bugs + perturbation."""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from etl_transbench.harness import (Task, discover_tasks, verify_candidate,
                                    compile_candidate)
from etl_transbench.perturb import perturb_task, build_mapping, _rename_df
from legato.core import diagnose

TASKS = {os.path.basename(d): Task.load(d) for d in discover_tasks(os.path.join(ROOT, "tasks"))}


def ref_source(tid):
    with open(os.path.join(ROOT, "tasks", tid, "reference.py")) as f:
        return f.read()


def check(task, code, expect_eq, label, expect_class=None):
    fn, err = compile_candidate(code)
    assert fn, f"{label}: compile failed: {err}"
    res = verify_candidate(task, fn)
    assert res.equivalent == expect_eq, (
        f"{label}: expected {expect_eq}, got {res.equivalent}: "
        f"{res.reports[-1] if res.reports else res.error}")
    if expect_class:
        assert diagnose(res)["class"] == expect_class, label
    print(f"PASS  {label}")


# ---- 1. every category exemplar: reference-as-candidate verifies equivalent ----
for tid, task in TASKS.items():
    res = verify_candidate(task, task.reference)
    assert res.equivalent, f"{tid}: oracle self-verification failed: {res.reports or res.error}"
    print(f"PASS  {tid}: oracle self-verifies")

# ---- 2. targeted classic-migration bugs per new category ----
bugs = [
    ("t2_cursor_balance",
     ('["account_id", "txn_date", "txn_seq"]', '["account_id", "txn_date"]'),
     "T2 missing cursor tie-break caught"),
    ("t2_cursor_balance",
     ('df["amount"].fillna(0)', 'df["amount"]'),
     "T2 NULL-adds-zero semantics bug caught"),
    ("t3_dataflow_orders",
     ('m["region"].fillna("UNKNOWN")', 'm["region"]'),
     "T3 lookup on_miss default dropped caught"),
    ("t3_dataflow_orders",
     ('m["discount"].fillna(0)', 'm["discount"]'),
     "T3 reformat NULL-discount bug caught"),
    ("t4_multistep_sales",
     ('how="inner"', 'how="left"'),
     "T4 join-type change leaks dropped stores caught"),
    ("t6_sessionize_events",
     ('gap > pd.Timedelta(minutes=30)', 'gap >= pd.Timedelta(minutes=30)'),
     "T6 strict-vs-inclusive 30-min boundary caught"),
    ("t7_reject_validation",
     ('if r["amount"] <= 0:\n            return "AMT_NONPOS"\n        if r["currency"] not in valid_ccy:\n            return "CCY_INVALID"',
      'if r["currency"] not in valid_ccy:\n            return "CCY_INVALID"\n        if r["amount"] <= 0:\n            return "AMT_NONPOS"'),
     "T7 rule-order (reason precedence) bug caught"),
    ("t8_cdc_merge",
     ('ev = ev[ev["event_ts"] > wm]', 'ev = ev[ev["event_ts"] >= wm]'),
     "T8 watermark off-by-one (replay) caught"),
    ("t8_cdc_merge",
     ('["product_id", "event_ts", "event_seq"]', '["product_id", "event_ts"]'),
     "T8 event_seq tie-break dropped caught"),
]
for tid, (old, new), label in bugs:
    src = ref_source(tid)
    assert old in src, f"{label}: bug template no longer matches reference"
    check(TASKS[tid], src.replace(old, new), False, label,
          expect_class="semantic_divergence")

# ---- 3. perturbation harness ----
base = TASKS["t1_dialect_qualify"]
pt = perturb_task(base, seed=7)
mapping = build_mapping(base, 7)

# 3a. no canonical identifier survives in the perturbed artifact
for ident in ["acct_txn", "account_id", "txn_ts", "amount", "channel",
              "latest_high_value_txn", "size_band"]:
    assert not re.search(rf"\b{ident}\b", pt.legacy_artifact, re.IGNORECASE), \
        f"perturbation leak: {ident}"
print("PASS  perturbation: no canonical identifiers leak into artifact")

# 3b. a correct candidate written against PERTURBED names verifies equivalent
T1_GOOD_TEMPLATE = '''
import pandas as pd
def run(inputs):
    df = inputs["{acct_txn}"]
    df = df[df["{amount}"] > 100].copy()
    df = df.sort_values(["{txn_ts}", "{txn_id}"], ascending=[False, False])
    df = df.groupby("{account_id}", as_index=False).head(1)
    def band(a):
        if a >= 1000: return "JUMBO"
        if a >= 500:  return "LARGE"
        return "STANDARD"
    df["{size_band}"] = df["{amount}"].map(band)
    cols = ["{account_id}","{txn_id}","{txn_ts}","{amount}","{channel}","{size_band}"]
    return {{"{latest_high_value_txn}": df[cols]}}
'''
code = T1_GOOD_TEMPLATE.format(**{k: mapping[k] for k in
        ["acct_txn", "amount", "txn_ts", "txn_id", "account_id",
         "size_band", "channel", "latest_high_value_txn"]})
check(pt, code, True, "perturbation: perturbed-space candidate verifies equivalent")

# 3c. same candidate in CANONICAL names fails against the perturbed task
with open(os.path.join(ROOT, "tasks", "t1_dialect_qualify", "reference.py")) as f:
    pass  # canonical candidate below uses original names
canonical_code = T1_GOOD_TEMPLATE.format(
    acct_txn="acct_txn", amount="amount", txn_ts="txn_ts", txn_id="txn_id",
    account_id="account_id", size_band="size_band", channel="channel",
    latest_high_value_txn="latest_high_value_txn")
fn, _ = compile_candidate(canonical_code)
res = verify_candidate(pt, fn)
assert not res.equivalent
print("PASS  perturbation: memorized canonical solution no longer passes")

print(f"\nALL TESTS PASSED ({len(TASKS)} categories, {len(bugs)} bug probes, perturbation harness)")
