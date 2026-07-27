import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: tightly INTERLEAVED web/app events where the
    per-user gap never exceeds 25 min but the per-channel gap does — user-level
    sessionization merges sessions that must split, and channel events
    'bridging' another channel's gap must not keep it alive; within-channel
    ties broken by event_id; boundary gaps 25:00 vs 25:01."""
    rng = np.random.default_rng(seed)
    rows, eid = [], 1
    for uid in range(1, 28):
        t = pd.Timestamp("2025-03-05 09:00:00")
        # alternating channels every ~14 min: per-user gap 14m, per-channel 28m (> 25 splits)
        for j in range(int(rng.integers(16, 30))):
            ch = "WEB" if j % 2 == 0 else "APP"
            t = t + pd.Timedelta(minutes=float(rng.choice([12, 13, 14, 15])))
            rows.append(dict(user_id=uid, channel=ch, event_id=eid, event_ts=t)); eid += 1
        # then a same-channel burst with boundary gaps
        for gap in [24, 25, 25.0166667, 10]:
            t = t + pd.Timedelta(minutes=gap)
            rows.append(dict(user_id=uid, channel="WEB", event_id=eid, event_ts=t)); eid += 1
    # within-channel timestamp tie: event_id order decides
    ts = pd.Timestamp("2025-03-06 12:00:00")
    for e2 in range(2):
        rows.append(dict(user_id=900, channel="APP", event_id=eid, event_ts=ts)); eid += 1
    return {"events": pd.DataFrame(rows).sample(frac=1, random_state=seed)
            .reset_index(drop=True)}
