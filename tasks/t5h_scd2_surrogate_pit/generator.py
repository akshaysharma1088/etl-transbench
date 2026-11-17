import numpy as np
import pandas as pd

def corpus(seed: int):
    """Customers with one or two versions; staged changes, no-ops, new customers
    and reactivations arrive in shuffled order with non-contiguous ids, so the
    surrogate-key order matters. Facts sit on version boundaries, on the staged
    update date, before history, in closed gaps and on unknown customers."""
    rng = np.random.default_rng(seed)
    segs = np.array(["SMB", "MID", "ENT", None], dtype=object)
    base = pd.Timestamp("2023-01-01")
    dim, stg, fact = [], [], []
    sk = 1000
    ids = rng.choice(np.arange(10, 400), size=70, replace=False)
    upd = {}
    for cid in ids:
        cid = int(cid)
        seg0, seg1 = segs[rng.integers(0, 4)], segs[rng.integers(0, 4)]
        s0 = base + pd.Timedelta(days=int(rng.integers(0, 120)))
        s1 = s0 + pd.Timedelta(days=int(rng.integers(30, 200)))
        shape = rng.choice(["one", "two", "closed"], p=[0.5, 0.35, 0.15])
        sk += int(rng.integers(1, 4))
        if shape == "one":
            dim.append(dict(customer_sk=sk, customer_id=cid, segment=seg0, eff_start_date=s0,
                            eff_end_date=pd.NaT, is_current=1))
            cur_seg, cur_start = seg0, s0
        else:
            dim.append(dict(customer_sk=sk, customer_id=cid, segment=seg0, eff_start_date=s0,
                            eff_end_date=s1, is_current=0))
            if shape == "two":
                sk += 1
                dim.append(dict(customer_sk=sk, customer_id=cid, segment=seg1, eff_start_date=s1,
                                eff_end_date=pd.NaT, is_current=1))
            cur_seg, cur_start = (seg1, s1) if shape == "two" else (None, s1)
        u = cur_start + pd.Timedelta(days=int(rng.integers(40, 300)))
        r = rng.random()
        if r < 0.45:
            stg.append(dict(customer_id=cid, segment=segs[rng.integers(0, 4)], update_date=u))
            upd[cid] = u
        elif r < 0.6 and shape != "closed":
            stg.append(dict(customer_id=cid, segment=cur_seg, update_date=u))   # no-op
        for d in (s0, s0 - pd.Timedelta(days=1), s1, s1 - pd.Timedelta(days=1), u, u - pd.Timedelta(days=1),
                  u + pd.Timedelta(days=int(rng.integers(1, 50)))):
            if rng.random() < 0.45:
                fact.append(dict(customer_id=cid, txn_date=d, amount=round(float(rng.uniform(5, 900)), 2)))
    for cid in (3, 7, 405, 406, 407, 9001):                 # brand-new customers, low and high ids
        u = base + pd.Timedelta(days=int(rng.integers(300, 600)))
        stg.append(dict(customer_id=cid, segment=segs[rng.integers(0, 3)], update_date=u))
        fact.append(dict(customer_id=cid, txn_date=u, amount=10.0))
        fact.append(dict(customer_id=cid, txn_date=u - pd.Timedelta(days=1), amount=11.0))
    for cid in (5000, 5001):                                # customers the dimension never sees
        fact.append(dict(customer_id=cid, txn_date=base + pd.Timedelta(days=200), amount=1.5))
    dim = pd.DataFrame(dim).sample(frac=1, random_state=seed).reset_index(drop=True)
    dim["eff_end_date"] = pd.to_datetime(dim["eff_end_date"])
    stg = pd.DataFrame(stg).sample(frac=1, random_state=seed + 1).reset_index(drop=True)
    fact = pd.DataFrame(fact).sample(frac=1, random_state=seed + 2).reset_index(drop=True)
    fact.insert(0, "txn_id", np.arange(1, len(fact) + 1))
    return {"dim_customer": dim, "stg_customer": stg, "fact_txn": fact}
