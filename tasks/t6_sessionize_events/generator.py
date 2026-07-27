import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np, pandas as pd

def corpus(seed):
    rng = np.random.default_rng(seed)
    rows, eid = [], 1
    for uid in range(1, 31):
        t = pd.Timestamp("2025-05-01 08:00:00")
        for _ in range(int(rng.integers(5, 25))):
            # adversarial gaps clustered around the 30-minute boundary:
            gap_min = float(rng.choice([1, 5, 29, 30, 30, 31, 90, 240],
                                       p=[.2,.2,.1,.15,.05,.1,.1,.1]))
            t = t + pd.Timedelta(minutes=gap_min)
            rows.append(dict(user_id=uid, event_id=eid, event_ts=t))
            eid += 1
    return {"events": pd.DataFrame(rows)}
