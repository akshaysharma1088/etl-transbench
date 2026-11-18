import numpy as np
import pandas as pd


def corpus(seed: int):
    """Sessions nested inside longer ones, chains that only connect through a
    long early session, gaps of exactly 5 minutes and just over, the same device
    twice in a group, zero-length sessions and identical start times."""
    rng = np.random.default_rng(seed)
    rows = []
    base = pd.Timestamp("2024-09-10 07:00:00")
    for uid in range(1, 61):
        t = base + pd.Timedelta(minutes=int(rng.integers(0, 300)))
        for _ in range(int(rng.integers(2, 9))):
            dur = int(rng.choice([0, 3, 10, 25, 90]))
            rows.append(dict(user_id=uid, device_id=str(rng.choice(["phone", "laptop", "tablet"])),
                             start_ts=t, end_ts=t + pd.Timedelta(minutes=dur)))
            if rng.random() < 0.35:                                   # nested short session
                n0 = t + pd.Timedelta(minutes=int(rng.integers(0, max(dur, 1))))
                rows.append(dict(user_id=uid, device_id=str(rng.choice(["phone", "laptop", "tablet"])),
                                 start_ts=n0, end_ts=n0 + pd.Timedelta(minutes=int(rng.choice([0, 1, 2])))))
            step = int(rng.choice([0, 2, dur, dur + 4, dur + 5, dur + 6, dur + 20, dur + 120]))
            t = t + pd.Timedelta(minutes=step)
    df = pd.DataFrame(rows).sample(frac=1, random_state=seed).reset_index(drop=True)
    df.insert(0, "session_id", rng.permutation(np.arange(1, len(df) + 1)))
    return {"device_sessions": df}
