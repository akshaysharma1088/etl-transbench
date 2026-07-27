import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from etl_transbench.datagen import TableGen, ColumnGen, generate_corpus

TABLES = {
    "acct_txn": TableGen(
        name="acct_txn", rows=400, key_columns=["account_id"],
        duplicate_key_rate=0.6,   # many accounts with multiple txns
        columns=[
            ColumnGen("account_id", "int", null_rate=0.0, low=1, high=80),
            ColumnGen("txn_id", "int", null_rate=0.0, low=1, high=10_000_000),
            ColumnGen("txn_ts", "timestamp", null_rate=0.0),
            ColumnGen("amount", "float", null_rate=0.06, low=0, high=2000,
                      boundary_values=[100.0, 100.0000001, 499.999, 500.0, 999.99, 1000.0]),
            ColumnGen("channel", "category", null_rate=0.04, empty_rate=0.0,
                      categories=["WEB", "ATM ", "BRANCH", "MOBILE"]),
        ]),
}

def corpus(seed: int):
    """Adversarial augmentation (paper Sec. 5.1): inject timestamp ties within
    accounts so that translations missing the txn_id tie-break are detected."""
    import numpy as np
    import pandas as pd
    data = generate_corpus(TABLES, seed)
    df = data["acct_txn"]
    rng = np.random.default_rng(seed + 999)
    sample = df[df["amount"] > 100].head(15)
    tied = sample.copy()
    tied["txn_id"] = tied["txn_id"] + rng.integers(1, 1000, size=len(tied))  # same ts, new id
    tied["amount"] = tied["amount"] + 50.0
    data["acct_txn"] = pd.concat([df, tied], ignore_index=True)
    return data
