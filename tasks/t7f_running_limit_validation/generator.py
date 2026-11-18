import numpy as np
import pandas as pd


def corpus(seed: int):
    """Days where a large transfer is rejected and a later small one fits,
    totals that land exactly on the limit, references repeated after an
    accepted row and after a rejected row, unknown accounts and bad amounts
    that would otherwise also be duplicates or over the limit."""
    rng = np.random.default_rng(seed)
    limits = pd.DataFrame({"account_id": np.arange(1, 21),
                           "daily_limit": rng.choice([500.0, 1000.0, 2500.0], size=20)})
    days = [pd.Timestamp("2024-10-01") + pd.Timedelta(days=d) for d in range(3)]
    rows, n = [], 0
    for _ in range(420):
        acct = int(rng.integers(1, 21)) if rng.random() < 0.94 else int(rng.integers(90, 95))
        if rows and rng.random() < 0.16:
            ref = rows[int(rng.integers(0, len(rows)))]["transfer_ref"]
        else:
            n += 1
            ref = f"TR{n:05d}"
        amt = float(rng.choice([50.0, 100.0, 250.0, 400.0, 500.0, 900.0, 1500.0]))
        r = rng.random()
        amt = None if r < 0.03 else 0.0 if r < 0.05 else -25.0 if r < 0.07 else amt
        rows.append(dict(transfer_ref=ref, account_id=acct, amount=amt, transfer_date=days[rng.integers(0, 3)]))
    df = pd.DataFrame(rows)
    df.insert(0, "row_num", rng.permutation(np.arange(1, len(df) + 1)) * 5)
    return {"account_limits": limits, "transfers": df.sample(frac=1, random_state=seed).reset_index(drop=True)}
