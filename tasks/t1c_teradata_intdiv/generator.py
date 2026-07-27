import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from etl_transbench.datagen import TableGen, ColumnGen, generate_corpus

TABLES = {
    "acct_balance": TableGen(
        name="acct_balance", rows=400, key_columns=["account_id"],
        columns=[
            ColumnGen("account_id", "int", null_rate=0.0, low=1, high=100_000),
            ColumnGen("balance_cents", "float", null_rate=0.08,
                      low=-250_000, high=250_000,
                      boundary_values=[-150.0, -100.0, -99.0, -1.0,
                                       99.0, 100.0, 150.0, 199.0]),
            ColumnGen("fx_rate", "float", null_rate=0.0, low=0.5, high=2.0,
                      boundary_values=[1.0]),
            ColumnGen("acct_type", "category", null_rate=0.0,
                      categories=["RETAIL", "CORP", "CLOSED"]),
        ]),
}

def corpus(seed: int):
    """Adversarial augmentation: force NEGATIVE balances that are not multiples
    of 100 into open accounts — the only inputs on which trunc-toward-zero
    (legacy) and floor division (naive Python //) disagree."""
    import numpy as np, pandas as pd
    data = generate_corpus(TABLES, seed)
    df = data["acct_balance"]
    rng = np.random.default_rng(seed + 4242)
    neg = df[df["acct_type"] != "CLOSED"].head(25).copy()
    neg["account_id"] = neg["account_id"] + 1_000_000       # fresh keys
    neg["balance_cents"] = -(rng.integers(1, 5000, size=len(neg)) * 100 +
                             rng.integers(1, 100, size=len(neg))).astype(float)
    data["acct_balance"] = pd.concat([df, neg], ignore_index=True)
    return data
