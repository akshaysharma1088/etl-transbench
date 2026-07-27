import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: batches engineered at EXACTLY 20% bad (must
    NOT quarantine — strict >), just over (1 bad in 4 = 25% quarantines,
    2 in 10 = 20% doesn't), boundary values exactly 0 and 1000 (valid),
    and integer-arithmetic traps (20% of 35 rows = 7 exactly)."""
    rng = np.random.default_rng(seed)
    rows = []
    rid = 1
    def add_batch(bid, n, n_bad):
        nonlocal rid
        for j in range(n):
            if j < n_bad:
                v = float(rng.choice([np.nan, -5.0, 1200.0]))
            else:
                v = float(rng.choice([0.0, 1000.0, rng.uniform(1, 999)]))
            rows.append(dict(batch_id=bid, reading_id=rid,
                             sensor=f"S{int(rng.integers(1, 9))}", value=v))
            rid += 1
    add_batch(1, 10, 2)     # 20.00% -> NOT quarantined
    add_batch(2, 10, 3)     # 30% -> quarantined
    add_batch(3, 4, 1)      # 25% -> quarantined
    add_batch(4, 35, 7)     # exactly 20% on awkward n -> NOT quarantined
    add_batch(5, 35, 8)     # 22.86% -> quarantined
    add_batch(6, 50, 0)     # clean batch
    for bid in range(7, 18):
        n = int(rng.integers(8, 40))
        add_batch(bid, n, int(rng.integers(0, max(2, n // 3))))
    df = pd.DataFrame(rows)
    return {"readings": df.sample(frac=1, random_state=seed).reset_index(drop=True)}
