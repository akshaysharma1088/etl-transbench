"""Verification for the confirmation set: ten hard, stateful tasks written
after the repair method was fixed, used once to compare the methods.

For every task the oracle verifies against itself (including the replay pass
where one is declared), and each planted defect, a plausible mistranslation
made by editing the oracle's own source, is caught.
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
from etl_transbench.harness import Task, compile_candidate, verify_candidate  # noqa: E402

PROBES = {
    "t8f_positions_versioned_cdc": [
        ("no replay guard", 'e["row_version"] <= guard[k]', "False"),
        ("a zero quantity is stored, not treated as a close", 'if e["op"] == "D" or e["qty"] == 0:', 'if e["op"] == "D":'),
        ("version ties applied in the wrong order", '.sort_values(["row_version", "batch_seq"])',
         '.sort_values(["row_version", "batch_seq"], ascending=[True, False])'),
    ],
    "t8g_partial_update_sentinel": [
        ("NULL overwrites the field", 'if pd.isna(c[f]):\n                continue\n            new = _value(f, c[f])',
         "new = None if pd.isna(c[f]) else _value(f, c[f])"),
        ("a no-op change advances the watermark", 'if changed:\n            row["updated_seq"]', 'if True:\n            row["updated_seq"]'),
        ("email stored without normalising", 'return str(v).strip().lower() if field == "email" else v', "return v"),
    ],
    "t8h_inventory_movements": [
        ("a rejected movement is recorded as applied",
         'rejects.append(dict(line_no=m["line_no"], reason="INSUFFICIENT_STOCK"))\n            continue',
         'rejects.append(dict(line_no=m["line_no"], reason="INSUFFICIENT_STOCK"))\n            seen.add(m["movement_id"])\n            continue'),
        ("stock is allowed to go negative", 'if cur + int(m["qty"]) < 0:', "if False:"),
        ("lines processed in line_no order only", '.sort_values(["movement_ts", "line_no"])', '.sort_values(["line_no"])'),
    ],
    "t8i_snapshot_diff_changelog": [
        ("trailing spaces treated as a change", 'str(a).rstrip(" ") != str(b).rstrip(" ")', "str(a) != str(b)"),
        ("NULL compared as equal to a value", "return an != bn", "return False"),
        ("changed columns listed alphabetically", '("price", "stock", "label")', '("label", "price", "stock")'),
    ],
    "t2e_overdraft_fee_cursor": [
        ("a fee on every overdrawing debit", " and day not in charged", ""),
        ("the fee is not fed back into the balance", "bal = round(bal - FEE, 2)\n                charged.add(day)", "charged.add(day)"),
        ("a deposit can trigger the fee", 'if t["amount"] < 0 and bal < 0', "if bal < 0"),
    ],
    "t2f_fifo_lot_matching": [
        ("newest lot consumed first", "for lot in lots:", "for lot in reversed(lots):"),
        ("a sell with nothing to match is dropped", "sells.append(dict(trade_id", '(int(t["qty"]) - need > 0) and sells.append(dict(trade_id'),
    ],
    "t2g_payment_waterfall": [
        ("newest invoice paid first", '.sort_values(["customer_id", "due_date", "invoice_id"])',
         '.sort_values(["customer_id", "due_date", "invoice_id"], ascending=[True, False, True])'),
        ("partly paid invoices reported as open", '("PARTIAL" if i["touched"] else "OPEN")', '"OPEN"'),
        ("payments applied in payment_id order", '.sort_values(["customer_id", "paid_ts", "payment_id"])',
         '.sort_values(["customer_id", "payment_id"])'),
    ],
    "t5i_scd2_future_dated": [
        ("the open-ended version is always current",
         'int(r["eff_start_date"] <= b and (pd.isna(r["eff_end_date"]) or b < r["eff_end_date"]))', 'int(pd.isna(r["eff_end_date"]))'),
        ("a repeated price creates a version",
         'if tail is not None and float(tail["list_price"]) == float(s["list_price"]):', "if False:"),
        ("staged rows applied in arrival order", '.sort_values(["product_id", "effective_date"])', ""),
    ],
    "t6f_cross_device_session_merge": [
        ("group end follows the last session", 'cur["end_ts"] = max(cur["end_ts"], s["end_ts"])', 'cur["end_ts"] = s["end_ts"]'),
        ("a gap of exactly five minutes splits", '<= cur["end_ts"] + GAP', '< cur["end_ts"] + GAP'),
        ("devices counted per session", 'len(r.pop("_devices"))', 'r["source_count"] + 0 * len(r.pop("_devices"))'),
    ],
    "t7f_running_limit_validation": [
        ("rejected rows count towards the limit",
         'bad.append(dict(row_num=r["row_num"], reason=reason))\n            continue',
         'bad.append(dict(row_num=r["row_num"], reason=reason))\n            if reason == "OVER_LIMIT":\n'
         '                totals[key] = totals.get(key, 0.0) + float(r["amount"])\n            continue'),
        ("a rejected row reserves its reference",
         'bad.append(dict(row_num=r["row_num"], reason=reason))\n            continue',
         'bad.append(dict(row_num=r["row_num"], reason=reason))\n            refs.add(r["transfer_ref"])\n            continue'),
        ("a total equal to the limit is rejected", '> float(limit[r["account_id"]]):', '>= float(limit[r["account_id"]]):'),
    ],
}

n = 0
for tid, probes in PROBES.items():
    task = Task.load(os.path.join(ROOT, "tasks", tid))
    assert task.meta.get("set") == "confirmation", tid
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

print(f"\nALL CONFIRMATION TASKS VERIFIED ({len(PROBES)} oracles, {n} bug probes)")
