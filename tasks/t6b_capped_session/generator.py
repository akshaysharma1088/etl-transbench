import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: long trains of sub-20-minute gaps that cross
    the 4-hour cap WITHOUT any gap break (gap-only translations under-split);
    events landing EXACTLY at start+4h (stay) and just past it (split); gaps
    exactly 20:00 (stay) and 20:01 (split); and post-cap trains verifying the
    cap re-anchors to the NEW session start rather than a fixed grid (fixed
    4h-bucket translations diverge on the second cap window)."""
    rng = np.random.default_rng(seed)
    rows, eid = [], 1
    for uid in range(1, 25):
        t = pd.Timestamp("2025-06-01 07:00:00")
        rows.append(dict(user_id=uid, event_id=eid, event_ts=t)); eid += 1
        for _ in range(int(rng.integers(25, 60))):
            gap_min = float(rng.choice(
                [3, 8, 15, 19, 20, 20.0166667, 21, 45],
                p=[.25, .2, .15, .1, .08, .07, .05, .1]))
            t = t + pd.Timedelta(minutes=gap_min)
            rows.append(dict(user_id=uid, event_id=eid, event_ts=t)); eid += 1
    # surgical cap-boundary train: 16 events 16 min apart => crosses 4h at #16
    t = pd.Timestamp("2025-06-02 09:00:00")
    for j in range(18):
        rows.append(dict(user_id=500, event_id=eid,
                         event_ts=t + pd.Timedelta(minutes=16 * j))); eid += 1
    # exactly-at-cap event: second event at start+4h exactly, third just past
    base = pd.Timestamp("2025-06-03 10:00:00")
    for uid, offs in [(600, [0, 240, 240.0166667]), (601, [0, 239, 241])]:
        for o in offs:
            rows.append(dict(user_id=uid, event_id=eid,
                             event_ts=base + pd.Timedelta(minutes=o))); eid += 1
    return {"events": pd.DataFrame(rows).sample(frac=1, random_state=seed)
            .reset_index(drop=True)}
