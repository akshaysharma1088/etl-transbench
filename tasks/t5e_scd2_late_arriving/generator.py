import numpy as np
import pandas as pd

def corpus(seed: int):
    """Accounts with one to three existing versions. Staging mixes dates inside
    old versions (splits), dates on a version start (corrections), dates before
    the first version, dates after the current start, repeats of the covering
    plan (no-ops), several records for one account, and brand-new accounts."""
    rng = np.random.default_rng(seed)
    plans = np.array(["FREE", "PLUS", "PRO", None], dtype=object)
    base = pd.Timestamp("2023-01-01")
    dim, stg = [], []
    for aid in range(1, 61):
        n = int(rng.integers(1, 4))
        starts = np.sort(rng.choice(np.arange(30, 600), size=n, replace=False))
        prev = None
        for i, off in enumerate(starts):
            plan = plans[rng.integers(0, 4)]
            while i and (plan == prev or (plan is None and prev is None)):
                plan = plans[rng.integers(0, 4)]
            prev = plan
            end = base + pd.Timedelta(days=int(starts[i + 1])) if i + 1 < n else pd.NaT
            dim.append(dict(account_id=aid, plan=plan, eff_start_date=base + pd.Timedelta(days=int(off)),
                            eff_end_date=end, is_current=int(i + 1 == n)))
        used = set()
        for _ in range(int(rng.integers(0, 4))):
            kind = rng.random()
            if kind < 0.20:
                off = int(starts[rng.integers(0, n)])                 # on a version start
            elif kind < 0.30:
                off = int(rng.integers(0, starts[0]))                 # before history
            elif kind < 0.45:
                off = int(starts[-1] + rng.integers(1, 200))          # after the current start
            else:
                off = int(rng.integers(starts[0], starts[-1] + 100))  # somewhere inside
            if off in used:
                continue
            used.add(off)
            d = base + pd.Timedelta(days=off)
            if rng.random() < 0.2:                                    # repeat the covering plan
                cover = [r for r in dim if r["account_id"] == aid and r["eff_start_date"] <= d
                         and (pd.isna(r["eff_end_date"]) or d < r["eff_end_date"])]
                plan = cover[0]["plan"] if cover else plans[rng.integers(0, 4)]
            else:
                plan = plans[rng.integers(0, 4)]
            stg.append(dict(account_id=aid, plan=plan, update_date=d))
    for aid in range(300, 306):                                       # new accounts, two records each
        d0 = base + pd.Timedelta(days=int(rng.integers(100, 500)))
        stg.append(dict(account_id=aid, plan="PLUS", update_date=d0 + pd.Timedelta(days=20)))
        stg.append(dict(account_id=aid, plan="FREE", update_date=d0))
    dim = pd.DataFrame(dim)
    dim["eff_end_date"] = pd.to_datetime(dim["eff_end_date"])
    stg = pd.DataFrame(stg).sample(frac=1, random_state=seed).reset_index(drop=True)
    return {"dim_account": dim, "stg_account": stg}
