import pandas as pd

def run(inputs):
    p = inputs["payments"].copy()
    valid_ccy = {"USD", "EUR", "GBP"}

    def reason(r):
        if pd.isna(r["amount"]):
            return "AMT_NULL"
        if r["amount"] <= 0:
            return "AMT_NONPOS"
        if r["currency"] not in valid_ccy:
            return "CCY_INVALID"
        if pd.isna(r["country"]):
            return "CTRY_NULL"
        return None

    p["reason_code"] = p.apply(reason, axis=1)
    clean = p[p["reason_code"].isna()].copy()
    clean["amount"] = clean["amount"].round(2)
    rejects = p[p["reason_code"].notna()].copy()
    return {"payments_clean": clean[["payment_id","amount","currency","country"]],
            "payments_rejects": rejects[["payment_id","amount","currency",
                                         "country","reason_code"]]}
