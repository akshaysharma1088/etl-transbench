import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: MOST carriers have several rate rows
    (duplicate lookup keys) with same-date ties broken by rate_id, so a naive
    left merge explodes row counts AND picks wrong rates; some carriers miss
    entirely (on_miss defaults); physical order of the rate table shuffled so
    'first physical row' != 'first_by policy row'."""
    rng = np.random.default_rng(seed)
    n = 300
    shipments = pd.DataFrame({
        "shipment_id": np.arange(1, n + 1),
        "carrier_id": rng.integers(1, 40, n),        # 30-39 exist, 35+ some miss
        "weight_kg": rng.uniform(0.5, 800, n).round(2),
    })
    rows = []
    rid = 1
    for cid in range(1, 33):                          # carriers 33-39 missing
        k = int(rng.integers(1, 5))                   # 1-4 rate rows each
        base_dates = rng.choice(pd.date_range("2024-01-01", "2025-06-01", freq="D"), k)
        for d in base_dates:
            rows.append((rid, cid, pd.Timestamp(d),
                         float(rng.uniform(0.2, 8.0)),
                         str(rng.choice(["Gold", "SILVER", "BRONZE"]))))
            rid += 1
        if k >= 2:                                    # same-date tie, rate_id decides
            rows.append((rid, cid, pd.Timestamp(base_dates[0]),
                         float(rng.uniform(0.2, 8.0)), "TIEBREAK"))
            rid += 1
    rates = pd.DataFrame(rows, columns=["rate_id", "carrier_id",
                                        "effective_date", "rate_per_kg",
                                        "service_tier"])
    rates = rates.sample(frac=1, random_state=seed).reset_index(drop=True)
    return {"shipments": shipments, "carrier_rates": rates}
