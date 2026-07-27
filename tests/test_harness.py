"""End-to-end harness tests.

Proves the scientific machinery works without any LLM:
  1. A correct candidate verifies as equivalent on both tasks.
  2. Classic migration bugs are caught:
     - T1: WHERE applied after the window (filter/window order bug)
     - T1: missing tie-break column (nondeterministic latest-row bug)
     - T5: new version created for unchanged records (SCD2 over-versioning)
     - T5: NULL-vs-NULL treated as a change (null semantics bug)
  3. The diagnoser classifies failures correctly.
"""
import os
import sys

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from etl_transbench.harness import Task, verify_candidate, compile_candidate  # noqa: E402
from legato.core import diagnose  # noqa: E402

T1 = Task.load(os.path.join(ROOT, "tasks", "t1_dialect_qualify"))
T5 = Task.load(os.path.join(ROOT, "tasks", "t5_scd2_customer"))


# ---------------- correct candidates ----------------

T1_GOOD = '''
import pandas as pd
def run(inputs):
    df = inputs["acct_txn"]
    df = df[df["amount"] > 100].copy()                       # WHERE before window
    df = df.sort_values(["txn_ts", "txn_id"], ascending=[False, False])
    df = df.groupby("account_id", as_index=False).head(1)
    def band(a):
        if a >= 1000: return "JUMBO"
        if a >= 500:  return "LARGE"
        return "STANDARD"
    df["size_band"] = df["amount"].map(band)
    cols = ["account_id","txn_id","txn_ts","amount","channel","size_band"]
    return {"latest_high_value_txn": df[cols]}
'''

T1_BUG_FILTER_ORDER = T1_GOOD.replace(
    'df = df[df["amount"] > 100].copy()                       # WHERE before window\n'
    '    df = df.sort_values(["txn_ts", "txn_id"], ascending=[False, False])\n'
    '    df = df.groupby("account_id", as_index=False).head(1)',
    'df = df.sort_values(["txn_ts", "txn_id"], ascending=[False, False])\n'
    '    df = df.groupby("account_id", as_index=False).head(1)\n'
    '    df = df[df["amount"] > 100].copy()                   # BUG: filter after window'
)

T1_BUG_NO_TIEBREAK = T1_GOOD.replace(
    '["txn_ts", "txn_id"], ascending=[False, False]',
    '["txn_ts"], ascending=[False]'
)

with open(os.path.join(ROOT, "tasks", "t5_scd2_customer", "reference.py")) as f:
    T5_GOOD = f.read()  # the reference itself, as a stand-in correct candidate

T5_BUG_OVERVERSION = T5_GOOD.replace(
    'if _neq(c["name"], s["name"]) or _neq(c["segment"], s["segment"]):',
    'if True:  # BUG: versions even unchanged records'
)

T5_BUG_NULL_SEMANTICS = T5_GOOD.replace(
    '    if an and bn:\n        return False\n', 
    '    if an and bn:\n        return True   # BUG: NULL vs NULL treated as change\n'
)


def check(task, code, expect_equivalent, expect_class=None, label=""):
    fn, err = compile_candidate(code)
    assert fn is not None, f"{label}: compile failed: {err}"
    res = verify_candidate(task, fn)
    assert res.equivalent == expect_equivalent, (
        f"{label}: expected equivalent={expect_equivalent}, got {res.equivalent}; "
        f"reports={res.reports[-1] if res.reports else res.error}")
    if not expect_equivalent and expect_class:
        d = diagnose(res)
        assert d["class"] == expect_class, f"{label}: expected {expect_class}, got {d['class']}"
    print(f"PASS  {label}")


if __name__ == "__main__":
    check(T1, T1_GOOD, True, label="T1 correct candidate verifies equivalent")
    check(T1, T1_BUG_FILTER_ORDER, False, "semantic_divergence",
          "T1 filter-after-window bug caught + classified")
    check(T1, T1_BUG_NO_TIEBREAK, False, "semantic_divergence",
          "T1 missing-tiebreak bug caught + classified")
    check(T5, T5_GOOD, True, label="T5 correct candidate verifies equivalent")
    check(T5, T5_BUG_OVERVERSION, False, "semantic_divergence",
          "T5 over-versioning bug caught + classified")
    check(T5, T5_BUG_NULL_SEMANTICS, False, "semantic_divergence",
          "T5 null-semantics bug caught + classified")

    # runtime-failure diagnosis path
    fn, _ = compile_candidate("def run(inputs):\n    return inputs['nope']\n")
    res = verify_candidate(T1, fn)
    assert not res.executed and diagnose(res)["class"] == "runtime"
    print("PASS  runtime failure diagnosed as 'runtime'")

    # schema-mismatch diagnosis path
    fn, _ = compile_candidate(
        "def run(inputs):\n"
        "    d = inputs['acct_txn'].copy()\n"
        "    return {'latest_high_value_txn': d[['account_id']]}\n")
    res = verify_candidate(T1, fn)
    assert diagnose(res)["class"] == "schema_mismatch"
    print("PASS  schema mismatch diagnosed as 'schema_mismatch'")
    print("\nALL TESTS PASSED")
