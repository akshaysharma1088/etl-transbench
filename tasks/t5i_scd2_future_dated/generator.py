import numpy as np
import pandas as pd


def corpus(seed: int):
    """Products with one or two existing versions; staged rows before, on and
    after the batch date, several per product, repeats of the tail price
    (skipped) and a price that returns to an older value; brand-new products
    whose first version starts in the past or in the future."""
    rng = np.random.default_rng(seed)
    batch = pd.Timestamp("2024-06-15")
    prices = [9.99, 12.5, 15.0, 19.99, 24.0]
    dim, stg = [], []
    for pid in range(1, 71):
        s0 = batch - pd.Timedelta(days=int(rng.integers(200, 400)))
        p0 = float(rng.choice(prices))
        if rng.random() < 0.4:
            s1 = s0 + pd.Timedelta(days=int(rng.integers(30, 120)))
            dim.append(dict(product_id=pid, list_price=float(rng.choice([p for p in prices if p != p0])),
                            eff_start_date=s0, eff_end_date=s1, is_current=0))
            s0 = s1
        dim.append(dict(product_id=pid, list_price=p0, eff_start_date=s0, eff_end_date=pd.NaT, is_current=1))
        offs = set()
        for _ in range(int(rng.integers(0, 5))):
            off = int(rng.choice([-60, -30, -10, -1, 0, 1, 7, 30, 90]))
            if off in offs or batch + pd.Timedelta(days=off) <= s0:
                continue
            offs.add(off)
            stg.append(dict(product_id=pid, list_price=float(rng.choice([p0, p0] + prices)),
                            effective_date=batch + pd.Timedelta(days=off)))
    for pid in range(200, 212):
        for off in sorted(set(rng.choice([-20, 0, 5, 40], size=int(rng.integers(1, 4))).tolist())):
            stg.append(dict(product_id=pid, list_price=float(rng.choice(prices)),
                            effective_date=batch + pd.Timedelta(days=int(off))))
    d = pd.DataFrame(dim)
    d["eff_end_date"] = pd.to_datetime(d["eff_end_date"])
    s = pd.DataFrame(stg).sample(frac=1, random_state=seed).reset_index(drop=True)
    return {"dim_price": d, "stg_price": s, "batch_control": pd.DataFrame({"batch_date": [batch]})}
