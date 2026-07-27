import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: items with MULTI-EVENT chains where order
    matters — R,R,R accumulation (latest-wins loses receipts), A-then-R
    (reset then add), D-then-R re-creation from zero, D-then-A re-creation
    absolute, chains ending in D; events exactly AT the watermark (skip) and
    just after (apply); event_ts ties broken by event_seq (R+A same ts)."""
    rng = np.random.default_rng(seed)
    wm = pd.Timestamp("2025-07-01 00:00:00")
    snap = pd.DataFrame({
        "item_id": np.arange(1, 40),
        "qty_on_hand": rng.integers(0, 500, 39).astype(float),
        "last_event_ts": wm - pd.Timedelta(days=1),
    })
    evs = []
    seq = 1
    def ev(iid, op, qty, ts):
        nonlocal seq
        evs.append(dict(event_seq=seq, event_ts=ts, op=op, item_id=iid, qty=qty))
        seq += 1
    t0 = wm + pd.Timedelta(hours=1)
    for iid in range(1, 30):
        k = int(rng.integers(1, 6))
        ts = t0 + pd.Timedelta(minutes=int(rng.integers(0, 500)))
        pattern = rng.choice(["RRR", "AR", "DR", "DA", "RD", "R", "A"])
        for j, op in enumerate(pattern[:k] if len(pattern) >= k else pattern):
            ev(iid, op, float(rng.integers(1, 80)), ts + pd.Timedelta(minutes=7 * j))
    # watermark boundary: exactly at (skip) vs 1s after (apply)
    ev(35, "A", 7777.0, wm)                              # skipped
    ev(36, "A", 8888.0, wm + pd.Timedelta(seconds=1))    # applied
    # same-ts tie: R then A (A wins by seq) and A then R (adds on top)
    tt = t0 + pd.Timedelta(hours=9)
    ev(37, "R", 10.0, tt); ev(37, "A", 100.0, tt)
    ev(38, "A", 100.0, tt); ev(38, "R", 10.0, tt)
    # brand-new item via receipts only
    ev(500, "R", 5.0, t0); ev(500, "R", 6.0, t0 + pd.Timedelta(minutes=1))
    events = pd.DataFrame(evs).sample(frac=1, random_state=seed).reset_index(drop=True)
    return {"target_snapshot": snap, "cdc_events": events,
            "watermark": pd.DataFrame({"high_ts": [wm]})}
