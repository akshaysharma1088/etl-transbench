import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from etl_transbench.datagen import TableGen, ColumnGen, generate_corpus

TABLES = {
    "regional_txn": TableGen(
        name="regional_txn", rows=500, key_columns=[],
        columns=[
            ColumnGen("txn_id", "int", null_rate=0.0, low=1, high=10_000_000),
            ColumnGen("txn_ts", "timestamp", null_rate=0.0),
            ColumnGen("region", "category", null_rate=0.10,
                      categories=["NORTH", "SOUTH", "EAST", "WEST", "XX"]),
            ColumnGen("amount", "float", null_rate=0.12, low=-500, high=5000),
            ColumnGen("status", "category", null_rate=0.0,
                      categories=["POSTED", "PENDING", "VOID"]),
        ]),
}

def corpus(seed: int):
    """Adversarial augmentation: guarantee NULL regions and NULL amounts inside
    POSTED rows so DECODE-null-match and NVL-in-SUM/COUNT bugs are detected,
    plus same-month/same-region collision mass for grouping checks."""
    import numpy as np, pandas as pd
    data = generate_corpus(TABLES, seed)
    df = data["regional_txn"]
    posted = df[df["status"] == "POSTED"].head(20).copy()
    posted["region"] = None                       # DECODE NULL-match probe
    posted_null_amt = df[df["status"] == "POSTED"].tail(20).copy()
    posted_null_amt["amount"] = float("nan")      # NVL-in-aggregate probe
    data["regional_txn"] = pd.concat([df, posted, posted_null_amt],
                                     ignore_index=True)
    return data
