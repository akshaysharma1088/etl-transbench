"""Executable legacy oracle for t3b_dup_lookup_first.
Legacy lookup resolves duplicate carrier_ids to exactly one row (latest
effective_date, then highest rate_id) BEFORE joining, so output row count
always equals input row count. Misses default rate 0.0 / tier NONE."""
import pandas as pd

def run(inputs):
    s = inputs["shipments"]
    r = inputs["carrier_rates"].sort_values(
        ["carrier_id", "effective_date", "rate_id"],
        ascending=[True, False, False])
    r1 = r.drop_duplicates("carrier_id", keep="first")[
        ["carrier_id", "rate_per_kg", "service_tier"]]
    m = s.merge(r1, on="carrier_id", how="left")
    m["rate_per_kg"] = m["rate_per_kg"].fillna(0.0)
    m["service_tier"] = m["service_tier"].fillna("NONE")
    m["freight_cost"] = m["weight_kg"] * m["rate_per_kg"]
    cols = ["shipment_id", "carrier_id", "service_tier", "weight_kg",
            "rate_per_kg", "freight_cost"]
    return {"shipment_costs": m[cols]}
