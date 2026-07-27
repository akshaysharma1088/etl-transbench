import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: accounts with MULTIPLE history rows so a
    Type-1 email overwrite must touch expired versions too; email-only
    changes (no version allowed), tier-only changes (version, email carried),
    combined changes; NULL email <-> value transitions in both directions;
    unchanged records; staging duplicates with date ties."""
    rng = np.random.default_rng(seed)
    tiers = np.array(["BRONZE", "SILVER", "GOLD"], dtype=object)
    dim_rows, stg_rows = [], []
    for aid in range(1, 70):
        email = None if rng.random() < 0.12 else f"a{aid}@old.com"
        tier = tiers[rng.integers(0, 3)]
        start = pd.Timestamp("2023-02-01") + pd.Timedelta(days=int(rng.integers(0, 300)))
        if rng.random() < 0.5:                       # expired history row
            dim_rows.append(dict(acct_id=aid, email=email, tier="BRONZE",
                                 eff_start_date=start - pd.Timedelta(days=500),
                                 eff_end_date=start, is_current=0))
        dim_rows.append(dict(acct_id=aid, email=email, tier=tier,
                             eff_start_date=start, eff_end_date=pd.NaT, is_current=1))
        upd = pd.Timestamp("2024-09-01") + pd.Timedelta(days=int(rng.integers(0, 60)))
        r = rng.random()
        if r < 0.22:                                  # email-only change
            stg_rows.append(dict(acct_id=aid, email=f"a{aid}@new.com", tier=tier,
                                 update_date=upd))
        elif r < 0.44:                                # tier-only change
            stg_rows.append(dict(acct_id=aid, email=email,
                                 tier=tiers[(list(tiers).index(tier) + 1) % 3],
                                 update_date=upd))
        elif r < 0.62:                                # combined change
            stg_rows.append(dict(acct_id=aid, email=f"a{aid}@both.com",
                                 tier=tiers[(list(tiers).index(tier) + 1) % 3],
                                 update_date=upd))
        elif r < 0.78:                                # unchanged
            stg_rows.append(dict(acct_id=aid, email=email, tier=tier,
                                 update_date=upd))
        # else: not staged
        if r < 0.10:                                  # duplicate with date tie
            stg_rows.append(dict(acct_id=aid, email=f"a{aid}@tie.com", tier=tier,
                                 update_date=upd))
    for aid in range(300, 306):                       # brand-new accounts
        stg_rows.append(dict(acct_id=aid, email=f"n{aid}@ex.com",
                             tier="SILVER",
                             update_date=pd.Timestamp("2024-09-15")))
    dim = pd.DataFrame(dim_rows)
    stg = pd.DataFrame(stg_rows).sample(frac=1, random_state=seed).reset_index(drop=True)
    return {"dim_acct": dim, "stg_acct": stg}
