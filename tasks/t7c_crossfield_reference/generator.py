import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: whitelists WITH SPACES after commas ('US, CA')
    so untrimmed membership checks reject valid countries; empty-string AND
    NULL whitelists (allow all); orders failing MULTIPLE rules where only the
    FIRST applies (suspended customer + discontinued sku -> CUST_INACTIVE);
    unknown customers/skus."""
    rng = np.random.default_rng(seed)
    ref_customers = pd.DataFrame({
        "customer_id": np.arange(1, 60),
        "status": rng.choice(["ACTIVE", "SUSPENDED", "CLOSED"], 59, p=[.7, .2, .1]),
    })
    sku_ids = [f"SKU{i:03d}" for i in range(1, 40)]
    wl_choices = ["US,CA", "US, CA, MX", " GB ,FR", "", None, "US"]
    ref_skus = pd.DataFrame({
        "sku": sku_ids,
        "discontinued": rng.choice([0, 0, 0, 1], 39),
        "allowed_countries": [wl_choices[int(rng.integers(0, len(wl_choices)))]
                              for _ in sku_ids],
    })
    n = 400
    orders = pd.DataFrame({
        "order_id": np.arange(1, n + 1),
        "customer_id": rng.integers(1, 75, n),          # 60-74 unknown
        "sku": [f"SKU{int(x):03d}" for x in rng.integers(1, 48, n)],  # 40-47 unknown
        "qty": rng.integers(1, 30, n).astype(float),
        "ship_country": rng.choice(["US", "CA", "MX", "GB", "FR", "BR"], n),
    })
    return {"orders": orders, "ref_customers": ref_customers, "ref_skus": ref_skus}
