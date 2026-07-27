import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: population mass in every rule-overlap region —
    amount>10000 with photos==0 matches BOTH high_value and manual_review and
    must land on the earlier rule (high_value); amounts exactly at the 500 and
    10000 boundaries with both photo states; plus disjoint populations for each
    single-rule region. With these rules every row matches at least one rule,
    so the default port stays empty by construction — first-match ordering,
    not port coverage, is what this task discriminates."""
    rng = np.random.default_rng(seed)
    blocks = []
    cid = 1
    def block(n, amt_lo, amt_hi, photos):
        nonlocal cid
        b = pd.DataFrame({
            "claim_id": np.arange(cid, cid + n),
            "amount": rng.uniform(amt_lo, amt_hi, n).round(2),
            "photos_attached": photos,
        })
        cid += n
        return b
    blocks.append(block(60, 10, 500, 1))          # fast_track
    blocks.append(block(50, 10001, 90000, 0))     # overlap r2/r3 -> high_value
    blocks.append(block(50, 10001, 90000, 1))     # r2 only -> high_value
    blocks.append(block(60, 501, 10000, 1))       # r3 via amount
    blocks.append(block(60, 10, 500, 0))          # r3 via photos
    boundary = pd.DataFrame({
        "claim_id": np.arange(cid, cid + 4),
        "amount": [500.0, 500.0, 10000.0, 10000.0],
        "photos_attached": [1, 0, 1, 0],
    })
    df = pd.concat(blocks + [boundary], ignore_index=True)
    return {"claims": df.sample(frac=1, random_state=seed).reset_index(drop=True)}
