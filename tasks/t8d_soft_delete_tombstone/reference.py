"""Executable legacy oracle for t8d_soft_delete_tombstone.
Soft deletes with a sticky 7-day window: an update within 7 days of a
deletion is discarded; strictly after 7 days it resurrects the user."""
import pandas as pd

def run(inputs):
    snap = {r["user_id"]: dict(email=r["email"], status=r["status"],
                               ts=r["status_ts"])
            for r in inputs["target_snapshot"].to_dict("records")}
    wm = inputs["watermark"]["high_ts"].iloc[0]
    ev = inputs["cdc_events"]
    ev = ev[ev["event_ts"] > wm].sort_values(["event_ts", "event_seq"])
    win = pd.Timedelta(days=7)
    for e in ev.to_dict("records"):
        uid = e["user_id"]
        cur = snap.get(uid)
        if e["op"] == "D":
            if cur is not None:
                snap[uid] = dict(email=cur["email"], status="DELETED",
                                 ts=e["event_ts"])
        else:  # 'U'
            if cur is not None and cur["status"] == "DELETED":
                if e["event_ts"] - cur["ts"] > win:
                    snap[uid] = dict(email=e["email"], status="ACTIVE",
                                     ts=e["event_ts"])
                # else: sticky window, discard
            else:
                snap[uid] = dict(email=e["email"], status="ACTIVE",
                                 ts=e["event_ts"])
    out = pd.DataFrame([dict(user_id=k, email=v["email"], status=v["status"],
                             status_ts=v["ts"]) for k, v in snap.items()])
    return {"new_snapshot": out[["user_id", "email", "status", "status_ts"]]}
