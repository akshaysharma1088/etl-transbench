"""Executable legacy oracle for t7c_crossfield_reference.
Ordered first-failure validation against two reference tables; the country
whitelist is comma-delimited with members TRIMMED; empty/NULL list = allow
all."""
import pandas as pd

def run(inputs):
    o = inputs["orders"].copy()
    cust = inputs["ref_customers"].set_index("customer_id")["status"].to_dict()
    skus = inputs["ref_skus"].set_index("sku")
    def reason(r):
        if r["customer_id"] not in cust:
            return "CUST_UNKNOWN"
        if cust[r["customer_id"]] != "ACTIVE":
            return "CUST_INACTIVE"
        if r["sku"] not in skus.index:
            return "SKU_UNKNOWN"
        row = skus.loc[r["sku"]]
        if int(row["discontinued"]) == 1:
            return "SKU_DISC"
        ac = row["allowed_countries"]
        if not (pd.isna(ac) or str(ac).strip() == ""):
            allowed = {c.strip() for c in str(ac).split(",")}
            if r["ship_country"] not in allowed:
                return "CTRY_BLOCKED"
        return None
    o["reason_code"] = o.apply(reason, axis=1)
    clean = o[o["reason_code"].isna()]
    rejects = o[o["reason_code"].notna()]
    cols = ["order_id", "customer_id", "sku", "qty", "ship_country"]
    return {"orders_clean": clean[cols],
            "orders_rejects": rejects[cols + ["reason_code"]]}
