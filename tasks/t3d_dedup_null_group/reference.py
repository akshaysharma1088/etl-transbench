"""Executable legacy oracle for t3d_dedup_null_group.
Dedup keeps LAST per meter_id in (read_ts, read_seq) order = latest read.
Aggregator preserves NULL zone as its own group row."""
import pandas as pd

def run(inputs):
    df = inputs["meter_reads"].sort_values(
        ["meter_id", "read_ts", "read_seq"]).copy()
    latest = df.drop_duplicates("meter_id", keep="last")
    out = (latest.groupby("zone", dropna=False, as_index=False)
                 .agg(total_kwh=("kwh", "sum"),
                      meter_count=("kwh", "size")))
    return {"zone_totals": out[["zone", "total_kwh", "meter_count"]]}
