import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: the prior snapshot contains, for refreshed
    dates, PRODUCTS THAT DO NOT REAPPEAR in today's feed (merge/upsert-style
    translations wrongly keep them); zero/negative-qty rows in the feed
    (excluded by Step 1's qty>0); untouched partitions that must survive
    byte-identical; and a product appearing in BOTH prior and new for the same
    date with different values (new must win)."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2025-06-01", periods=10, freq="D")
    prior_rows = []
    for d in dates[:7]:                              # prior covers days 1-7
        for pid in rng.choice(np.arange(1, 60), size=25, replace=False):
            prior_rows.append((pid, d, float(rng.integers(10, 500)),
                               round(float(rng.uniform(2, 40)), 4)))
    prior = pd.DataFrame(prior_rows, columns=["product_id", "batch_date",
                                              "total_qty", "max_unit_cost"])
    n = 600
    inbound = pd.DataFrame({
        "product_id": rng.integers(1, 45, n),        # products 45-59 never reappear
        "batch_date": rng.choice(dates[4:], n),      # refresh days 5-10 (5-7 overlap prior)
        "qty": rng.integers(-5, 60, n).astype(float),
        "unit_cost": rng.uniform(2, 40, n).round(4),
    })
    inbound.loc[rng.random(n) < 0.04, "qty"] = 0.0   # boundary: excluded
    return {"target_snapshot_prior": prior, "inbound": inbound}
