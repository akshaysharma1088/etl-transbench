import pandas as pd

def run(inputs):
    df = inputs["transactions"].sort_values(
        ["account_id", "txn_date", "txn_seq"]).copy()
    df["running_balance"] = (df["amount"].fillna(0)
                             .groupby(df["account_id"]).cumsum())
    df["overdraft_flag"] = (df["running_balance"] < 0).astype(int)
    return {"acct_balance_flags": df[["account_id", "txn_seq", "txn_date",
                                      "amount", "running_balance",
                                      "overdraft_flag"]]}
