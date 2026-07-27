import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: every user gets at least one MIDNIGHT-
    STRADDLING burst (small gaps across 00:00 — gap-only translations merge
    what must split), gaps exactly 45:00 (stay) vs 45:01 (split), and an
    event exactly AT midnight 00:00:00 (belongs to the NEW date)."""
    rng = np.random.default_rng(seed)
    rows, eid = [], 1
    for uid in range(1, 30):
        day = pd.Timestamp("2025-04-01") + pd.Timedelta(days=int(rng.integers(0, 5)))
        t = day + pd.Timedelta(hours=22, minutes=int(rng.integers(0, 50)))
        for _ in range(int(rng.integers(10, 22))):
            gap_min = float(rng.choice([2, 10, 30, 44, 45, 45.0166667, 46, 120],
                                       p=[.3, .2, .1, .1, .08, .07, .05, .1]))
            t = t + pd.Timedelta(minutes=gap_min)
            rows.append(dict(user_id=uid, event_id=eid, event_ts=t)); eid += 1
    # surgical: burst straddling midnight with 1-2 min gaps + exact-midnight event
    t0 = pd.Timestamp("2025-04-10 23:56:00")
    for uid in (700, 701):
        for o in [0, 2, 4, 6, 8]:                 # 23:56 .. 00:04
            rows.append(dict(user_id=uid, event_id=eid,
                             event_ts=t0 + pd.Timedelta(minutes=o))); eid += 1
        rows.append(dict(user_id=uid, event_id=eid,
                         event_ts=pd.Timestamp("2025-04-12 00:00:00"))); eid += 1
        rows.append(dict(user_id=uid, event_id=eid,
                         event_ts=pd.Timestamp("2025-04-11 23:59:00"))); eid += 1
    return {"events": pd.DataFrame(rows).sample(frac=1, random_state=seed)
            .reset_index(drop=True)}
