import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np, pandas as pd
from etl_transbench.datagen import TableGen, ColumnGen, generate_corpus

def corpus(seed):
    rng = np.random.default_rng(seed)
    n = 500
    df = pd.DataFrame({
        "account_id": rng.integers(1, 40, n),
        "txn_seq": np.arange(1, n + 1),
        "txn_date": pd.Timestamp("2025-01-01")
                    + pd.to_timedelta(rng.integers(0, 90, n), unit="D"),
        "amount": rng.uniform(-500, 500, n),
    })
    df.loc[rng.random(n) < 0.05, "amount"] = np.nan      # NULL adds zero probe
    # date-tie injection: same account, same date, differing txn_seq
    ties = df.head(12).copy()
    ties["txn_seq"] = ties["txn_seq"] + 10_000
    ties["amount"] = -ties["amount"].abs() - 1            # forces sign flips
    out = pd.concat([df, ties], ignore_index=True)
    # shuffle physical order so stable sorts cannot mask a missing tie-break
    return {"transactions": out.sample(frac=1, random_state=seed).reset_index(drop=True)}
