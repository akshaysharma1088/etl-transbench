"""Executable legacy oracle for t4b_delete_reinsert.
Partition-level refresh: every batch_date present in the new feed is fully
deleted from the prior snapshot (even products absent from today's feed for
that date), then today's aggregate is inserted. Untouched partitions carry
forward unchanged."""
import pandas as pd

def run(inputs):
    prior = inputs["target_snapshot_prior"]
    inbound = inputs["inbound"]
    stg = (inbound[inbound["qty"] > 0]
           .groupby(["product_id", "batch_date"], as_index=False)
           .agg(total_qty=("qty", "sum"),
                max_unit_cost=("unit_cost", "max")))
    refreshed_dates = stg["batch_date"].unique()
    kept = prior[~prior["batch_date"].isin(refreshed_dates)]
    out = pd.concat([kept, stg], ignore_index=True)
    return {"target_snapshot": out[["product_id", "batch_date",
                                    "total_qty", "max_unit_cost"]]}
