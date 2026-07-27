import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: invalid rows planted at account START (total
    must begin after them), MID-stream (total must skip, not zero), and as an
    account's ONLY rows (zero posted rows but a reject-count row must exist);
    zero-reject accounts included; boundary qty=0 rows (invalid: qty<=0) and
    unit_price=0 rows (VALID: price<0 is the test) included; shuffled."""
    rng = np.random.default_rng(seed)
    n = 450
    df = pd.DataFrame({
        "account_id": rng.integers(1, 35, n),
        "post_seq": np.arange(1, n + 1),
        "post_date": pd.Timestamp("2025-02-01")
                     + pd.to_timedelta(rng.integers(0, 45, n), unit="D"),
        "qty": rng.uniform(1, 50, n).round(2),
        "unit_price": rng.uniform(0.5, 200, n).round(4),
    })
    m = rng.random(n)
    df.loc[m < 0.04, "qty"] = np.nan
    df.loc[(m >= 0.04) & (m < 0.08), "qty"] = 0.0            # boundary: invalid
    df.loc[(m >= 0.08) & (m < 0.11), "unit_price"] = np.nan
    df.loc[(m >= 0.11) & (m < 0.13), "unit_price"] = -rng.uniform(1, 10, ((m >= 0.11) & (m < 0.13)).sum())
    df.loc[(m >= 0.13) & (m < 0.15), "unit_price"] = 0.0     # boundary: VALID
    # account whose only rows are invalid
    only_bad = pd.DataFrame({
        "account_id": [888, 888], "post_seq": [20_001, 20_002],
        "post_date": [pd.Timestamp("2025-02-05")] * 2,
        "qty": [np.nan, -3.0], "unit_price": [10.0, 5.0],
    })
    # clean account with zero rejects
    clean = pd.DataFrame({
        "account_id": [777] * 3, "post_seq": [30_001, 30_002, 30_003],
        "post_date": pd.to_datetime(["2025-02-02", "2025-02-03", "2025-02-04"]),
        "qty": [1.0, 2.0, 3.0], "unit_price": [10.0, 10.0, 10.0],
    })
    out = pd.concat([df, only_bad, clean], ignore_index=True)
    return {"postings": out.sample(frac=1, random_state=seed).reset_index(drop=True)}
