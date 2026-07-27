import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: STAGGERED per-device watermarks (a global
    min/max watermark translation misapplies late events for ahead devices or
    drops valid ones for behind devices); replay events exactly AT a device's
    watermark (skip); late events newer than OTHER devices' watermarks;
    devices with only-late batches (carry forward); ts ties by event_seq."""
    rng = np.random.default_rng(seed)
    base = pd.Timestamp("2025-07-10 00:00:00")
    snap_rows, evs = [], []
    seq = 1
    for dev in range(1, 45):
        wm_off = int(rng.integers(0, 96))            # staggered watermarks
        wm = base + pd.Timedelta(hours=wm_off)
        snap_rows.append(dict(device_id=dev,
                              reading=round(float(rng.uniform(10, 90)), 3),
                              applied_event_ts=wm))
        for _ in range(int(rng.integers(1, 5))):
            off = int(rng.integers(-48, 48))         # half land BEFORE the watermark
            ts = wm + pd.Timedelta(hours=off)
            evs.append(dict(event_seq=seq, event_ts=ts, device_id=dev,
                            reading=round(float(rng.uniform(10, 90)), 3)))
            seq += 1
        if rng.random() < 0.3:                       # exact replay at watermark
            evs.append(dict(event_seq=seq, event_ts=wm, device_id=dev,
                            reading=999.0))
            seq += 1
    # same-ts tie: two valid events, event_seq decides
    dev, wm = 44, base + pd.Timedelta(hours=10)
    tt = wm + pd.Timedelta(hours=5)
    evs.append(dict(event_seq=seq, event_ts=tt, device_id=1, reading=111.0)); seq += 1
    evs.append(dict(event_seq=seq, event_ts=tt, device_id=1, reading=222.0)); seq += 1
    # new devices
    for dev in (900, 901):
        evs.append(dict(event_seq=seq, event_ts=base + pd.Timedelta(hours=2),
                        device_id=dev, reading=50.0)); seq += 1
    snap = pd.DataFrame(snap_rows)
    events = pd.DataFrame(evs).sample(frac=1, random_state=seed).reset_index(drop=True)
    return {"target_snapshot": snap, "cdc_events": events}
