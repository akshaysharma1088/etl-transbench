"""Executable legacy oracle for t1c_teradata_intdiv.
Teradata INT/INT division truncates toward zero (numpy fix/trunc), NOT floor.
ZEROIFNULL applies before division. CAST(float AS INTEGER) also truncates
toward zero."""
import numpy as np

def run(inputs):
    df = inputs["acct_balance"]
    df = df[df["acct_type"] != "CLOSED"].copy()
    cents = df["balance_cents"].fillna(0.0)
    df["balance_bucket"] = np.trunc(cents / 100.0)            # toward zero
    df["fx_units"] = np.trunc(cents * df["fx_rate"] / 100.0)  # toward zero
    out = df[["account_id", "balance_bucket", "fx_units"]]
    return {"balance_buckets": out}
