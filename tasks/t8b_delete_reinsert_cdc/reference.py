"""Executable legacy oracle for t8b_delete_reinsert_cdc.
Delta CDC: every surviving event applies sequentially; 'R' adds, 'A' resets
absolute, 'D' removes (later events re-create). Latest-wins is wrong here."""
import pandas as pd

def run(inputs):
    snap = {r["item_id"]: dict(qty=r["qty_on_hand"], ts=r["last_event_ts"])
            for r in inputs["target_snapshot"].to_dict("records")}
    wm = inputs["watermark"]["high_ts"].iloc[0]
    ev = inputs["cdc_events"]
    ev = ev[ev["event_ts"] > wm].sort_values(["event_ts", "event_seq"])
    for e in ev.to_dict("records"):
        iid = e["item_id"]
        if e["op"] == "D":
            snap.pop(iid, None)
        elif e["op"] == "A":
            snap[iid] = dict(qty=float(e["qty"]), ts=e["event_ts"])
        else:  # 'R'
            cur = snap.get(iid, dict(qty=0.0, ts=None))
            snap[iid] = dict(qty=float(cur["qty"]) + float(e["qty"]),
                             ts=e["event_ts"])
    out = pd.DataFrame([dict(item_id=k, qty_on_hand=v["qty"],
                             last_event_ts=v["ts"]) for k, v in snap.items()])
    if len(out) == 0:
        out = pd.DataFrame(columns=["item_id", "qty_on_hand", "last_event_ts"])
    return {"new_snapshot": out[["item_id", "qty_on_hand", "last_event_ts"]]}
