"""Verification for new T7 and T8 tasks: oracle self-check + planted bugs."""
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

NEW = ["t7b_multi_reason_collect", "t7c_crossfield_reference",
       "t7d_quarantine_threshold", "t8b_delete_reinsert_cdc",
       "t8c_out_of_order_late", "t8d_soft_delete_tombstone"]
for tid in NEW:
    task = Task.load(os.path.join(ROOT, "tasks", tid))
    res = verify_candidate(task, task.reference)
    assert res.equivalent, f"{tid}: oracle self-verification FAILED: {res.reports or res.error}"
    print(f"PASS  {tid}: oracle self-verifies")

# t7b bug: first-match instead of collect-all
bug = '''
import pandas as pd
def run(inputs):
    df = inputs["invoices"].copy()
    def reason(r):
        if pd.isna(r["amount"]) or r["amount"] < 0: return "AMT_BAD"
        if pd.isna(r["tax"]) or r["tax"] < 0: return "TAX_BAD"
        if not pd.isna(r["amount"]) and not pd.isna(r["tax"]) and r["tax"] > r["amount"] * 0.5:
            return "TAX_EXCESS"
        if pd.isna(r["due_date"]): return "DUE_NULL"
        if pd.isna(r["customer_ref"]) or str(r["customer_ref"]).strip() == "": return "REF_EMPTY"
        return None
    df["reason_codes"] = df.apply(reason, axis=1)
    clean = df[df["reason_codes"].isna()]; rejects = df[df["reason_codes"].notna()]
    cols = ["invoice_id", "amount", "tax", "due_date", "customer_ref"]
    return {"invoices_clean": clean[cols], "invoices_rejects": rejects[cols + ["reason_codes"]]}
'''
check("t7b_multi_reason_collect", bug, False, "t7b: first-match vs collect-all -> caught")

# t7c bug: whitelist membership without trimming
bug = '''
import pandas as pd
def run(inputs):
    o = inputs["orders"].copy()
    cust = inputs["ref_customers"].set_index("customer_id")["status"].to_dict()
    skus = inputs["ref_skus"].set_index("sku")
    def reason(r):
        if r["customer_id"] not in cust: return "CUST_UNKNOWN"
        if cust[r["customer_id"]] != "ACTIVE": return "CUST_INACTIVE"
        if r["sku"] not in skus.index: return "SKU_UNKNOWN"
        row = skus.loc[r["sku"]]
        if int(row["discontinued"]) == 1: return "SKU_DISC"
        ac = row["allowed_countries"]
        if not (pd.isna(ac) or str(ac).strip() == ""):
            allowed = set(str(ac).split(","))            # WRONG: no trim
            if r["ship_country"] not in allowed: return "CTRY_BLOCKED"
        return None
    o["reason_code"] = o.apply(reason, axis=1)
    clean = o[o["reason_code"].isna()]; rejects = o[o["reason_code"].notna()]
    cols = ["order_id", "customer_id", "sku", "qty", "ship_country"]
    return {"orders_clean": clean[cols], "orders_rejects": rejects[cols + ["reason_code"]]}
'''
check("t7c_crossfield_reference", bug, False, "t7c: untrimmed whitelist members -> caught")

# t7d bug: >= 20% quarantines (boundary batch wrongly moved)
bug = '''
import pandas as pd
def run(inputs):
    df = inputs["readings"].copy()
    df["bad"] = df["value"].isna() | (df["value"] < 0) | (df["value"] > 1000)
    stats = df.groupby("batch_id")["bad"].agg(["sum", "size"])
    stats["pct"] = stats["sum"] * 100.0 / stats["size"]
    quarantined = set(stats.index[stats["sum"] * 100 >= stats["size"] * 20])   # WRONG: >=
    df["batch_reject_pct"] = df["batch_id"].map(stats["pct"].round(2))
    q = df[df["batch_id"].isin(quarantined)]; rest = df[~df["batch_id"].isin(quarantined)]
    cols = ["batch_id", "reading_id", "sensor", "value"]
    return {"readings_clean": rest[~rest["bad"]][cols],
            "readings_rejects": rest[rest["bad"]][cols],
            "readings_quarantine": q[cols + ["batch_reject_pct"]]}
'''
check("t7d_quarantine_threshold", bug, False, "t7d: >= vs strict > threshold -> caught")

# t8b bug: latest-wins collapsing (loses receipt accumulation)
bug = '''
import pandas as pd
def run(inputs):
    snap = {r["item_id"]: dict(qty=r["qty_on_hand"], ts=r["last_event_ts"])
            for r in inputs["target_snapshot"].to_dict("records")}
    wm = inputs["watermark"]["high_ts"].iloc[0]
    ev = inputs["cdc_events"]
    ev = ev[ev["event_ts"] > wm]
    ev = (ev.sort_values(["item_id", "event_ts", "event_seq"])
            .groupby("item_id", as_index=False).tail(1))          # WRONG: latest wins
    for e in ev.to_dict("records"):
        iid = e["item_id"]
        if e["op"] == "D": snap.pop(iid, None)
        elif e["op"] == "A": snap[iid] = dict(qty=float(e["qty"]), ts=e["event_ts"])
        else:
            cur = snap.get(iid, dict(qty=0.0, ts=None))
            snap[iid] = dict(qty=float(cur["qty"]) + float(e["qty"]), ts=e["event_ts"])
    out = pd.DataFrame([dict(item_id=k, qty_on_hand=v["qty"], last_event_ts=v["ts"])
                        for k, v in snap.items()])
    return {"new_snapshot": out[["item_id", "qty_on_hand", "last_event_ts"]]}
'''
check("t8b_delete_reinsert_cdc", bug, False, "t8b: latest-wins loses delta chain -> caught")

# t8c bug: global watermark (min of device watermarks)
bug = '''
import pandas as pd
def run(inputs):
    snap = inputs["target_snapshot"].copy()
    ev = inputs["cdc_events"].copy()
    gw = snap["applied_event_ts"].min()                            # WRONG: global
    keep = ev["event_ts"] > gw
    surv = (ev[keep].sort_values(["device_id", "event_ts", "event_seq"])
            .groupby("device_id", as_index=False).tail(1))
    snap = snap.set_index("device_id")
    for e in surv.to_dict("records"):
        snap.loc[e["device_id"], ["reading", "applied_event_ts"]] = (e["reading"], e["event_ts"])
    return {"new_snapshot": snap.reset_index()[["device_id", "reading", "applied_event_ts"]]}
'''
check("t8c_out_of_order_late", bug, False, "t8c: global vs per-device watermark -> caught")

# t8d bug: plain upsert resurrection (sticky window ignored)
bug = '''
import pandas as pd
def run(inputs):
    snap = {r["user_id"]: dict(email=r["email"], status=r["status"], ts=r["status_ts"])
            for r in inputs["target_snapshot"].to_dict("records")}
    wm = inputs["watermark"]["high_ts"].iloc[0]
    ev = inputs["cdc_events"]
    ev = ev[ev["event_ts"] > wm].sort_values(["event_ts", "event_seq"])
    for e in ev.to_dict("records"):
        uid = e["user_id"]; cur = snap.get(uid)
        if e["op"] == "D":
            if cur is not None:
                snap[uid] = dict(email=cur["email"], status="DELETED", ts=e["event_ts"])
        else:
            snap[uid] = dict(email=e["email"], status="ACTIVE", ts=e["event_ts"])   # WRONG
    out = pd.DataFrame([dict(user_id=k, email=v["email"], status=v["status"], status_ts=v["ts"])
                        for k, v in snap.items()])
    return {"new_snapshot": out[["user_id", "email", "status", "status_ts"]]}
'''
check("t8d_soft_delete_tombstone", bug, False, "t8d: sticky window ignored -> caught")

print("\nALL NEW T7/T8 TASKS VERIFIED (6 oracles, 6 bug probes)")
