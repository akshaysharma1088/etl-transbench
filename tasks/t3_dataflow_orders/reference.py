import pandas as pd

def run(inputs):
    o = inputs["orders"]
    c = inputs["customers"][["customer_id", "region"]]
    f = o[o["status"] == "SHIPPED"].copy()
    m = f.merge(c, on="customer_id", how="left")
    m["region"] = m["region"].fillna("UNKNOWN")          # on_miss default
    m["net_amount"] = m["qty"] * m["unit_price"] * (1 - m["discount"].fillna(0))
    cols = ["order_id", "customer_id", "region", "qty", "unit_price", "net_amount"]
    return {"shipped_orders_enriched": m[cols]}
