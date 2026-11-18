import numpy as np
import pandas as pd


def corpus(seed: int):
    """Accounts that hover around zero: several debits below zero on one day,
    deposits while negative, negative openings, a balance that lands exactly on
    zero, timestamp ties, days with no debit, and txns for unknown accounts."""
    rng = np.random.default_rng(seed)
    accts, txns, tid = [], [], 1
    day0 = pd.Timestamp("2024-07-01")
    for a in range(1, 51):
        accts.append(dict(account_id=a, opening_balance=float(rng.choice([-40.0, 0.0, 20.0, 50.0, 120.0, 400.0]))))
        for d in range(int(rng.integers(1, 5))):
            times = sorted(rng.choice(np.arange(8 * 60, 20 * 60, 15), size=int(rng.integers(1, 6)), replace=True))
            for m in times:
                amt = float(rng.choice([-120.0, -50.0, -20.0, -5.0, 20.0, 35.0, 50.0, 200.0],
                                       p=[0.12, 0.2, 0.2, 0.12, 0.12, 0.06, 0.1, 0.08]))
                txns.append(dict(account_id=a, txn_ts=day0 + pd.Timedelta(days=d, minutes=int(m)), amount=amt))
    for a in (900, 901):
        txns.append(dict(account_id=a, txn_ts=day0 + pd.Timedelta(hours=9), amount=-10.0))
    t = pd.DataFrame(txns).sample(frac=1, random_state=seed).reset_index(drop=True)
    t.insert(0, "txn_id", rng.permutation(np.arange(1, len(t) + 1)))
    return {"accounts": pd.DataFrame(accts), "txns": t}
