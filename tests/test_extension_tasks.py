"""Verification for the extension set (the harder tasks added in the revision).

For every task: the oracle verifies against itself on the default seeds, and
each planted defect, a plausible mistranslation made by editing the oracle's
own source, is caught. The replay check is exercised separately.
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
from etl_transbench.harness import Task, compile_candidate, verify_candidate  # noqa: E402

PROBES = {
    "t5e_scd2_late_arriving": [
        ("a late change is appended as the open current version",
         'eff_end_date=v["eff_end_date"], is_current=v["is_current"]', "eff_end_date=pd.NaT, is_current=1"),
        ("end date treated as inclusive", 'd < r["eff_end_date"]', 'd <= r["eff_end_date"]'),
        ("same-day correction creates a version", 'elif d == v["eff_start_date"]:', "elif False:"),
    ],
    "t5f_scd2_hash_detect": [
        ("NULL and empty string compared as different",
         'return "" if pd.isna(v) else', 'return "<NULL>" if pd.isna(v) else'),
        ("leading spaces trimmed as well", '.rstrip(" ")', ".strip()"),
        ("delimiter-safe comparison", 'return _part(city) + "|" + _part(tier)', "return (_part(city), _part(tier))"),
    ],
    "t5g_scd2_snapshot_close": [
        ("stores missing from the snapshot stay open", "if sid not in seen:", "if False:"),
        ("snapshot not deduplicated", ".drop_duplicates()", ""),
    ],
    "t5h_scd2_surrogate_pit": [
        ("surrogate keys numbered in staging order", '.sort_values("customer_id").to_dict', ".to_dict"),
        ("end date treated as inclusive in the fact lookup",
         'f["txn_date"] < r["eff_end_date"]', 'f["txn_date"] <= r["eff_end_date"]'),
        ("unmatched facts get NULL, not -1", "        sk = -1\n", "        sk = None\n"),
    ],
    "t3e_effective_lookup_route": [
        ("tie on valid_from broken by highest list_id", "ascending=[False, True]", "ascending=[False, False]"),
        ("lookup key not normalised", "str(s).strip().upper()", "str(s)"),
        ("router tests BULK before REVIEW",
         'if flag == "NO_PRICE" or pd.isna(qty) or qty >= 100:\n            route = "REVIEW"\n        elif ext >= 1000:',
         'if (ext or 0) >= 1000:\n            route = "BULK"\n        elif flag == "NO_PRICE" or pd.isna(qty) or qty >= 100:\n'
         '            route = "REVIEW"\n        elif False:'),
        ("price valid in the future is used", '["valid_from"] <= o["order_date"]]', '["valid_from"] == by_sku[sku]["valid_from"]]'),
    ],
    "t6e_session_heartbeat_logout": [
        ("heartbeats refresh the inactivity clock",
         'cur["heartbeat_count"] += 1\n', 'cur["heartbeat_count"] += 1\n                    cur["session_end"] = ts\n'),
        ("logout does not close the session", 'if e["event_type"] == "logout":\n                cur = None', "pass"),
        ("gap of exactly 30 minutes starts a session", 'ts - cur["session_end"] > GAP:', 'ts - cur["session_end"] >= GAP:'),
    ],
    "t7e_shortcircuit_parse_dedupe": [
        ("lenient number parser", '[+-]?[0-9]+(\\.[0-9]{1,2})?', '[+-]?[0-9]+(\\.[0-9]*)?'),
        ("rejected rows count as the first occurrence",
         "        if reason:\n", "        if reason and pid:\n            seen.add(pid)\n        if reason:\n"),
        ("payment ids compared case-insensitively", "elif pid in seen:", "elif pid.upper() in {x.upper() for x in seen}:"),
    ],
    "t8e_cdc_ops_replay": [
        ("no replay guard", 'e["seq"] <= guard[oid]', "False"),
        ("update with NULL amount overwrites", 'if not (e["op"] == "U" and pd.isna(e["amount"])):', "if True:"),
        ("events applied in event_ts order", '.sort_values("seq")', '.sort_values("event_ts")'),
        ("duplicate delivery applied twice is harmless, but a delete keeps the row",
         "                del state[oid]\n", '                row["status"] = "DELETED"\n'),
    ],
}

n = 0
for tid, probes in PROBES.items():
    task = Task.load(os.path.join(ROOT, "tasks", tid))
    assert task.meta.get("set") == "extension", tid
    res = verify_candidate(task, task.reference)
    assert res.equivalent, f"{tid}: oracle self-verification failed: {res.error or res.reports[-1]}"
    with open(os.path.join(task.task_dir, "reference.py")) as f:
        src = f.read()
    for label, old, new in probes:
        assert old in src, f"{tid}: probe '{label}' no longer matches the oracle source"
        fn, err = compile_candidate(src.replace(old, new))
        assert fn, f"{tid}: probe '{label}' does not compile: {err}"
        assert not verify_candidate(task, fn).equivalent, f"{tid}: planted defect NOT caught: {label}"
        n += 1
    print(f"PASS  {tid}: oracle self-verifies, {len(probes)} planted defects caught")

# The replay check: a job that is right on the first pass and wrong when its
# own output is fed back must fail, and the report must say it failed on replay.
task = Task.load(os.path.join(ROOT, "tasks", "t8e_cdc_ops_replay"))
calls = {"n": 0}


def right_once(inputs):
    calls["n"] += 1
    out = task.reference(inputs)
    if calls["n"] % 2 == 0:                       # the second, replay, pass
        out["new_state"] = out["new_state"].assign(last_seq=out["new_state"]["last_seq"] + 1)
    return out


res = verify_candidate(task, right_once)
assert not res.equivalent and res.reports[-1].get("replay"), "replay check did not fire"
print("PASS  t8e: a job that is not idempotent fails the replay pass")

print(f"\nALL EXTENSION TASKS VERIFIED ({len(PROBES)} oracles, {n} bug probes, replay check)")
