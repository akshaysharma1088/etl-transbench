import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: every meter has MULTIPLE reads whose kwh
    differs sharply between first and last (keep-first vs keep-last visibly
    diverges); read_ts ties broken by read_seq; a NULL-zone meter population
    exists (dropna group probe); physical order shuffled."""
    rng = np.random.default_rng(seed)
    frames = []
    seq = 1
    for meter in range(1, 120):
        k = int(rng.integers(2, 6))
        ts = pd.Timestamp("2025-05-01") + pd.to_timedelta(
            np.sort(rng.integers(0, 30 * 24, k)), unit="h")
        kwh = np.linspace(rng.uniform(1, 50), rng.uniform(500, 3000), k)
        zone = rng.choice(["Z1", "Z2", "Z3", None], p=[0.3, 0.3, 0.25, 0.15])
        frames.append(pd.DataFrame({
            "meter_id": meter,
            "read_seq": np.arange(seq, seq + k),
            "read_ts": ts,
            "zone": zone,
            "kwh": kwh.round(3),
        }))
        seq += k
    # timestamp tie inside one meter: read_seq must decide "last"
    tie = pd.DataFrame({
        "meter_id": [500, 500], "read_seq": [90_001, 90_002],
        "read_ts": [pd.Timestamp("2025-05-15")] * 2,
        "zone": ["Z1", "Z1"], "kwh": [10.0, 9999.0],
    })
    out = pd.concat(frames + [tie], ignore_index=True)
    return {"meter_reads": out.sample(frac=1, random_state=seed).reset_index(drop=True)}
