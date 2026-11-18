"""Executable legacy oracle for t5g_scd2_snapshot_close.
Full-snapshot SCD2: a store missing from today's snapshot has its current row
closed, and a store with history but no current row is reactivated with a new
version."""
import pandas as pd


def _differs(a, b):
    an, bn = pd.isna(a), pd.isna(b)
    if an or bn:
        return an != bn
    return a != b


def run(inputs):
    b = inputs["batch_control"]["batch_date"].iloc[0]
    rows = inputs["dim_store"].to_dict("records")
    snap = inputs["stg_store_full"].drop_duplicates().sort_values("store_id")
    current = {r["store_id"]: r for r in rows if r["is_current"] == 1}
    seen = set()
    for s in snap.to_dict("records"):
        seen.add(s["store_id"])
        c = current.get(s["store_id"])
        if c is not None and not (_differs(c["region"], s["region"]) or _differs(c["format"], s["format"])):
            continue
        if c is not None:
            c["eff_end_date"] = b
            c["is_current"] = 0
        rows.append(dict(store_id=s["store_id"], region=s["region"], format=s["format"],
                         eff_start_date=b, eff_end_date=pd.NaT, is_current=1))
    for sid, c in current.items():
        if sid not in seen:
            c["eff_end_date"] = b
            c["is_current"] = 0
    out = pd.DataFrame(rows, columns=["store_id", "region", "format", "eff_start_date",
                                      "eff_end_date", "is_current"])
    return {"dim_store_out": out}
