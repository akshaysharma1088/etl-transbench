import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np, pandas as pd

def corpus(seed):
    rng = np.random.default_rng(seed)
    n = 400
    p = pd.DataFrame({
        "payment_id": np.arange(1, n + 1),
        "amount": rng.uniform(-50, 500, n).round(4),
        "currency": rng.choice(["USD","EUR","GBP","JPY","XXX"], n,
                               p=[.4,.2,.15,.15,.1]),
        "country": rng.choice(["US","DE","GB", None], n, p=[.4,.25,.25,.1]),
    })
    p.loc[rng.random(n) < 0.08, "amount"] = np.nan
    # adversarial: records failing MULTIPLE rules (probe rule precedence)
    multi = pd.DataFrame({
        "payment_id": np.arange(n + 1, n + 9),
        "amount": [np.nan, np.nan, -5.0, -1.0, 10.0, 10.0, np.nan, -2.0],
        "currency": ["XXX","USD","JPY","USD","JPY","XXX","JPY","JPY"],
        "country": [None,"US",None,"US",None,None,None,None],
    })
    return {"payments": pd.concat([p, multi], ignore_index=True)}
