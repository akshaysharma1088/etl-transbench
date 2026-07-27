"""Scripted stand-in 'model' for pipeline validation. NOT an LLM.

For each task it returns, on first call, a known-buggy variant of the
reference solution (exercising verification failure, diagnosis, and the
repair path) and, on the repair call, the corrected solution (exercising
SER@k>0 accounting). Two tasks are scripted to stay broken so the
human-handoff path and SER<1.0 reporting are exercised too.

Token/cost values recorded in the ledger are constants labeled 'scripted';
they exist only so the aggregation code paths run.
"""
from __future__ import annotations
import os
import re
from typing import Dict

from etl_transbench.harness import CostLedger

_BUGS = {  # task_id -> (find, replace) applied to the reference source
    "t2_cursor_balance": ('df["amount"].fillna(0)', 'df["amount"]'),
    "t3_dataflow_orders": ('m["region"].fillna("UNKNOWN")', 'm["region"]'),
    "t4_multistep_sales": ('how="inner"', 'how="left"'),
    "t6_sessionize_events": ('gap > pd.Timedelta(minutes=30)',
                             'gap >= pd.Timedelta(minutes=30)'),
    "t8_cdc_merge": ('ev["event_ts"] > wm', 'ev["event_ts"] >= wm'),
}
_NEVER_FIXED = {"t5_scd2_customer", "t7_reject_validation"}  # exercise handoff


def _reference_source(task_id: str) -> str:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if task_id == "__unknown__":
        return "def run(inputs):\n    raise RuntimeError('scripted: task unknown to mock')\n"
    path = os.path.join(here, "tasks", task_id, "reference.py")
    with open(path) as f:
        src = f.read()
    if task_id == "t1_dialect_qualify":
        # reference uses duckdb/__file__; swap in a pure-pandas equivalent
        return _T1_PANDAS
    return src


_T1_PANDAS = '''
import pandas as pd
def run(inputs):
    df = inputs["acct_txn"]
    df = df[df["amount"] > 100].copy()
    df = df.sort_values(["txn_ts", "txn_id"], ascending=[False, False])
    df = df.groupby("account_id", as_index=False).head(1)
    df["size_band"] = df["amount"].map(
        lambda a: "JUMBO" if a >= 1000 else ("LARGE" if a >= 500 else "STANDARD"))
    return {"latest_high_value_txn":
            df[["account_id","txn_id","txn_ts","amount","channel","size_band"]]}
'''


class MockLLMClient:
    """Drop-in for legato.core.LLMClient with scripted outputs."""
    models = {"cheap": "mock-scripted-cheap", "frontier": "mock-scripted-frontier"}

    def __init__(self):
        self._calls: Dict[str, int] = {}

    def complete(self, tier: str, system: str, user: str,
                 ledger: CostLedger, role: str, max_tokens: int = 4000) -> str:
        m = re.search(r"Task category: (T\d) \((.*?)\)", user)
        task_id = self._task_from_user(user)
        n = self._calls.get(task_id, 0)
        self._calls[task_id] = n + 1
        ledger.record(role, self.models[tier], tokens_in=1000, tokens_out=500,
                      usd=0.001 if tier == "cheap" else 0.01, wall_s=0.0)
        src = _reference_source(task_id)
        if task_id in _NEVER_FIXED:
            broken = src.replace("return {", "raise RuntimeError('scripted: unresolved')\n    return {", 1)
            return f"```python\n{broken}```"
        if n == 0 and task_id in _BUGS:
            old, new = _BUGS[task_id]
            return f"```python\n{src.replace(old, new)}```"
        return f"```python\n{src}```"

    @staticmethod
    def _task_from_user(user: str) -> str:
        m = re.search(r"\b(t\d[a-z]?_[a-z0-9_]+)\b", user)
        if m:
            return m.group(1)
        # fall back: identify by distinctive artifact content
        markers = {"QUALIFY ROW_NUMBER": "t1_dialect_qualify",
                   "SP_RUNNING_BALANCE": "t2_cursor_balance",
                   "lookup_relation": "t3_dataflow_orders",
                   "STG_DAILY": "t4_multistep_sales",
                   "SP_LOAD_DIM_CUSTOMER": "t5_scd2_customer",
                   "sessionize": "t6_sessionize_events",
                   "reject port": "t7_reject_validation",
                   "cdc_events": "t8_cdc_merge"}
        for marker, tid in markers.items():
            if marker in user:
                return tid
        # Phase-1 expansion added 24 variant tasks with no scripted bug.
        # Rather than abort the whole validation run, fall back to the
        # generic path: the mock returns the reference verbatim, which
        # exercises translate -> verify -> pass. Still NOT REPORTABLE.
        return "__unknown__"
