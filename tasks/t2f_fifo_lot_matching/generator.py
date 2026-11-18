import numpy as np
import pandas as pd


def corpus(seed: int):
    """Sells that span several lots, sells larger than the position (short),
    sells before any buy, buys after a short sell, exact lot exhaustion, and
    timestamp ties ordered by trade_id."""
    rng = np.random.default_rng(seed)
    rows = []
    base = pd.Timestamp("2024-02-05 09:30:00")
    for acct in range(1, 31):
        for sym in rng.choice(["AAA", "BBB", "CCC"], size=int(rng.integers(1, 3)), replace=False):
            t = base
            for _ in range(int(rng.integers(2, 10))):
                t = t + pd.Timedelta(minutes=int(rng.choice([0, 0, 5, 30, 240])))
                side = "BUY" if rng.random() < 0.55 else "SELL"
                rows.append(dict(account_id=acct, symbol=str(sym), side=side,
                                 qty=int(rng.choice([10, 10, 20, 25, 50, 100])),
                                 price=float(rng.choice([9.5, 10.0, 10.25, 11.0, 12.5, 20.0])), trade_ts=t))
    df = pd.DataFrame(rows).sample(frac=1, random_state=seed).reset_index(drop=True)
    df.insert(0, "trade_id", rng.permutation(np.arange(1, len(df) + 1)))
    return {"trades": df}
