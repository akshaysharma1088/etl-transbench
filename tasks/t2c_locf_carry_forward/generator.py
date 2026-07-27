import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: every account's FIRST observations include
    NULL rates (so a global ffill leaks the previous account's rate — detected),
    date ties broken by obs_seq, and physical shuffle so account blocks are
    interleaved in storage order."""
    rng = np.random.default_rng(seed)
    frames = []
    seq = 1
    for acct in range(1, 26):
        n = int(rng.integers(8, 25))
        dates = (pd.Timestamp("2025-01-06")
                 + pd.to_timedelta(np.sort(rng.integers(0, 40, n)), unit="D"))
        rate = rng.uniform(0.5, 8.5, n)
        null_mask = rng.random(n) < 0.35
        null_mask[0] = True                      # leading NULL: leakage probe
        if n > 3:
            null_mask[1] = rng.random() < 0.6    # sometimes two leading NULLs
        rate = np.where(null_mask, np.nan, rate)
        frames.append(pd.DataFrame({
            "account_id": acct,
            "obs_seq": np.arange(seq, seq + n),
            "obs_date": dates,
            "rate": rate,
        }))
        seq += n
    out = pd.concat(frames, ignore_index=True)
    return {"rate_feed": out.sample(frac=1, random_state=seed).reset_index(drop=True)}
