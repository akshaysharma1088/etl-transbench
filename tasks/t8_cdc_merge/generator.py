import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np, pandas as pd

def corpus(seed):
    rng = np.random.default_rng(seed)
    np_, ne = 60, 150
    wm = pd.Timestamp("2025-04-15 00:00:00")
    snap = pd.DataFrame({
        "product_id": np.arange(1, np_ + 1),
        "name": [f"PROD_{i:03d}" for i in range(1, np_ + 1)],
        "price": rng.uniform(1, 100, np_).round(2),
        "last_event_ts": wm - pd.Timedelta(days=10),
    })
    ev = pd.DataFrame({
        "event_seq": np.arange(1, ne + 1),
        "event_ts": wm + pd.to_timedelta(rng.integers(-3*86400, 5*86400, ne),
                                         unit="s"),    # some BEFORE watermark
        "op": rng.choice(["I", "U", "D"], ne, p=[.2, .6, .2]),
        "product_id": rng.integers(1, np_ - 6, ne),     # ids 55-60 reserved below
        "name": [f"PROD_{i:03d}_NEW" for i in rng.integers(1, 999, ne)],
        "price": rng.uniform(1, 100, ne).round(2),
    })
    # adversarial: same product, IDENTICAL event_ts, differing event_seq/op
    tie_ts = wm + pd.Timedelta(days=1)
    ties = pd.DataFrame({
        "event_seq": [9002, 9001, 9004, 9003],   # physical order != seq order
        "event_ts": [tie_ts] * 4,
        "op": ["U", "D", "D", "U"],
        "product_id": [59, 59, 60, 60],
        "name": ["TIE_A", "TIE_B", "TIE_C", "TIE_D"],
        "price": [11.0, 12.0, 13.0, 14.0],
    })
    # adversarial: events EXACTLY at the watermark (must be SKIPPED under
    # the correct strict '>' filter) on reserved ids untouched by random events
    boundary = pd.DataFrame({
        "event_seq": [9101, 9102, 9103],
        "event_ts": [wm, wm, wm],
        "op": ["U", "U", "D"],
        "product_id": [56, 57, 58],
        "name": ["WM_BOUNDARY_A", "WM_BOUNDARY_B", "WM_BOUNDARY_C"],
        "price": [999.99, 888.88, 777.77],
    })
    ev = pd.concat([ev, boundary], ignore_index=True)
    ev = ev.sample(frac=1, random_state=seed).reset_index(drop=True)  # defeat stable-sort masking
    return {"target_snapshot": snap,
            "cdc_events": pd.concat([ev, ties], ignore_index=True),
            "watermark": pd.DataFrame({"high_ts": [wm]})}
