import pandas as pd

def run(inputs):
    s = inputs["sales"]
    d = inputs["store_dim"]
    stg = (s[s["amount"].notna()]
           .groupby(["store_id", "sale_date"], as_index=False)
           .agg(gross=("amount", "sum"), txn_cnt=("amount", "size")))
    store_daily = stg.merge(d[["store_id", "region"]], on="store_id", how="inner")
    region_daily = (store_daily
                    .groupby(["region", "sale_date"], as_index=False)
                    .agg(region_gross=("gross", "sum"),
                         region_txn_cnt=("txn_cnt", "sum")))
    return {"store_daily": store_daily[["store_id", "sale_date", "gross",
                                        "txn_cnt", "region"]],
            "region_daily": region_daily}
