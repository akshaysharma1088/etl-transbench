import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np, pandas as pd

def corpus(seed):
    rng = np.random.default_rng(seed)
    n, nc = 300, 50
    orders = pd.DataFrame({
        "order_id": np.arange(1, n + 1),
        "customer_id": rng.integers(1, nc + 15, n),       # some miss the lookup
        "status": rng.choice(["SHIPPED", "OPEN", "CANCELLED"], n, p=[.5, .3, .2]),
        "qty": rng.integers(1, 20, n),
        "unit_price": rng.uniform(1, 500, n),
        "discount": rng.uniform(0, 0.4, n),
    })
    orders.loc[rng.random(n) < 0.08, "discount"] = np.nan  # NULL-discount probe
    customers = pd.DataFrame({
        "customer_id": np.arange(1, nc + 1),
        "region": rng.choice(["NA", "EMEA", "APAC", "LATAM"], nc),
    })
    return {"orders": orders, "customers": customers}
