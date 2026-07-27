"""Executable legacy oracle for t8c_out_of_order_late.
Per-device watermark: an event applies only if event_ts strictly exceeds the
device's applied_event_ts (equality = replay = skip). Latest surviving event
by (event_ts, event_seq) wins."""
import pandas as pd

def run(inputs):
    snap = inputs["target_snapshot"].copy()
    ev = inputs["cdc_events"].copy()
    m = ev.merge(snap[["device_id", "applied_event_ts"]],
                 on="device_id", how="left")
    keep = m["applied_event_ts"].isna() | (m["event_ts"] > m["applied_event_ts"])
    surv = (m[keep].sort_values(["device_id", "event_ts", "event_seq"])
            .groupby("device_id", as_index=False).tail(1))
    snap = snap.set_index("device_id")
    for e in surv.to_dict("records"):
        snap.loc[e["device_id"], ["reading", "applied_event_ts"]] = (
            e["reading"], e["event_ts"])
    out = snap.reset_index()[["device_id", "reading", "applied_event_ts"]]
    return {"new_snapshot": out}
