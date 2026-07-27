import pandas as pd

def run(inputs):
    snap = inputs["target_snapshot"].copy()
    ev = inputs["cdc_events"].copy()
    wm = inputs["watermark"]["high_ts"].iloc[0]

    ev = ev[ev["event_ts"] > wm]                               # watermark
    ev = (ev.sort_values(["product_id", "event_ts", "event_seq"])
            .groupby("product_id", as_index=False).tail(1))    # latest wins

    snap = snap.set_index("product_id")
    for e in ev.to_dict("records"):
        pid = e["product_id"]
        if e["op"] == "D":
            if pid in snap.index:
                snap = snap.drop(pid)
        else:
            snap.loc[pid, ["name", "price", "last_event_ts"]] = (
                e["name"], e["price"], e["event_ts"])
    out = snap.reset_index()[["product_id", "name", "price", "last_event_ts"]]
    return {"new_snapshot": out}
