import numpy as np
import pandas as pd

def corpus(seed: int):
    """Event streams with gaps on and around 30 minutes, heartbeats that bridge
    a gap without extending it, heartbeats before any activity and after a
    logout, activity straight after a logout, and timestamp ties."""
    rng = np.random.default_rng(seed)
    rows, eid = [], 1
    base = pd.Timestamp("2024-05-06 08:00:00")
    for uid in range(1, 61):
        t = base + pd.Timedelta(minutes=int(rng.integers(0, 600)))
        if rng.random() < 0.3:
            rows.append((uid, t - pd.Timedelta(minutes=5), "heartbeat"))      # before any activity
        last_activity = None
        for _ in range(int(rng.integers(3, 16))):
            r = rng.random()
            if r < 0.30 and last_activity is not None:
                gap = int(rng.choice([5, 10, 29, 30, 31, 45]))                # measured from last ACTIVITY
                rows.append((uid, last_activity + pd.Timedelta(minutes=gap), "heartbeat"))
                continue
            step = int(rng.choice([0, 1, 5, 12, 20, 29, 30, 31, 40, 75]))
            t = (last_activity if last_activity is not None else t) + pd.Timedelta(minutes=step)
            kind = str(rng.choice(["view", "click", "logout"], p=[0.5, 0.35, 0.15]))
            rows.append((uid, t, kind))
            last_activity = t
            if kind == "logout" and rng.random() < 0.5:
                rows.append((uid, t + pd.Timedelta(minutes=int(rng.choice([1, 10]))), "heartbeat"))
    for uid in (900, 901):                                                    # heartbeats only
        rows.append((uid, base, "heartbeat"))
        rows.append((uid, base + pd.Timedelta(minutes=3), "heartbeat"))
    df = pd.DataFrame(rows, columns=["user_id", "event_ts", "event_type"])
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    df.insert(0, "event_id", np.arange(1, len(df) + 1))
    return {"app_events": df}
