import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: heavy overlap between feed accounts and prior
    snapshot with DIFFERENT scores (delta-vs-zero visibly diverges if the
    delta is computed against the post-update snapshot: it would be all
    zeros); feed-only accounts (COALESCE 0 path); snapshot-only accounts
    (must vanish from both outputs); duplicate feed rows per account so AVG
    matters."""
    rng = np.random.default_rng(seed)
    overlap = np.arange(1, 60)
    feed_only = np.arange(60, 80)
    snap_only = np.arange(80, 95)
    rows = []
    for a in np.concatenate([overlap, feed_only]):
        for _ in range(int(rng.integers(1, 5))):
            rows.append((a, float(rng.uniform(300, 850))))
    feed = pd.DataFrame(rows, columns=["account_id", "score"])
    prior = pd.DataFrame({
        "account_id": np.concatenate([overlap, snap_only]),
        "avg_score": rng.uniform(300, 850, len(overlap) + len(snap_only)),
    })
    return {"score_feed": feed.sample(frac=1, random_state=seed).reset_index(drop=True),
            "score_snapshot_prior": prior}
