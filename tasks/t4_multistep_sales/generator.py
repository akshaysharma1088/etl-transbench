import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np, pandas as pd

def corpus(seed):
    rng = np.random.default_rng(seed)
    n, ns = 800, 30
    sales = pd.DataFrame({
        "store_id": rng.integers(1, ns + 8, n),           # some stores not in dim
        "sale_date": pd.Timestamp("2025-03-01")
                     + pd.to_timedelta(rng.integers(0, 14, n), unit="D"),
        "amount": rng.uniform(5, 300, n),
    })
    sales.loc[rng.random(n) < 0.06, "amount"] = np.nan    # excluded by Step 1
    dim = pd.DataFrame({"store_id": np.arange(1, ns + 1),
                        "region": rng.choice(["NORTH","SOUTH","EAST","WEST"], ns)})
    return {"sales": sales, "store_dim": dim}
