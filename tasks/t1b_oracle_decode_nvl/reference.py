"""Executable legacy oracle for t1b_oracle_decode_nvl.
Implements Oracle semantics explicitly: DECODE matches NULL=NULL; NVL(amount,0)
keeps null-amount rows in both SUM and COUNT(*); TRUNC(ts,'MM') = month start."""
import pandas as pd

def _decode_region(r):
    if pd.isna(r):
        return "MISSING"          # DECODE NULL-match semantics
    if r == "XX":
        return "UNKNOWN"
    return r

def run(inputs):
    df = inputs["regional_txn"]
    df = df[df["status"] == "POSTED"].copy()
    df["txn_month"] = df["txn_ts"].dt.to_period("M").dt.to_timestamp()
    df["region_norm"] = df["region"].apply(_decode_region)
    df["amount_nvl"] = df["amount"].fillna(0.0)
    out = (df.groupby(["txn_month", "region_norm"], as_index=False)
             .agg(total_amount=("amount_nvl", "sum"),
                  txn_count=("amount_nvl", "size")))
    return {"monthly_region_rollup": out}
