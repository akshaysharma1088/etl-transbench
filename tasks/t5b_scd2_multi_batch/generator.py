import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: many products receive 2-4 staged updates in
    one batch, including A->B->A flips (dedup-to-latest sees 'no change' vs
    the current row and drops the ENTIRE chain) and chains ending in a
    no-change record (must not version); unique dates per product; brand-new
    products with multi-update chains; staging physically shuffled."""
    rng = np.random.default_rng(seed)
    cats = np.array(["ELEC", "HOME", "TOYS", None], dtype=object)
    bands = np.array(["LOW", "MID", "HIGH"], dtype=object)
    dim_rows, stg_rows = [], []
    for pid in range(1, 50):
        cat = cats[rng.integers(0, len(cats))]
        band = bands[rng.integers(0, len(bands))]
        dim_rows.append(dict(product_id=pid, category=cat, price_band=band,
                             eff_start_date=pd.Timestamp("2023-05-01"),
                             eff_end_date=pd.NaT, is_current=1))
        k = int(rng.integers(0, 5))
        dates = pd.Timestamp("2024-07-01") + pd.to_timedelta(
            np.sort(rng.choice(np.arange(0, 90), size=k, replace=False)), unit="D")
        prev_cat, prev_band = cat, band
        for j, d in enumerate(dates):
            r = rng.random()
            if r < 0.25 and j == len(dates) - 1:
                new_cat, new_band = prev_cat, prev_band        # trailing no-op
            elif r < 0.55 and j >= 1:
                new_cat, new_band = cat, band                  # flip BACK (A->B->A)
            else:
                new_cat = cats[rng.integers(0, len(cats))]
                new_band = bands[rng.integers(0, len(bands))]
            stg_rows.append(dict(product_id=pid, category=new_cat,
                                 price_band=new_band, update_date=d))
            prev_cat, prev_band = new_cat, new_band
    for pid in range(200, 208):                                # brand-new chains
        d0 = pd.Timestamp("2024-08-01") + pd.Timedelta(days=int(rng.integers(0, 20)))
        stg_rows.append(dict(product_id=pid, category="ELEC", price_band="LOW",
                             update_date=d0))
        stg_rows.append(dict(product_id=pid, category="ELEC", price_band="HIGH",
                             update_date=d0 + pd.Timedelta(days=3)))
    dim = pd.DataFrame(dim_rows)
    stg = pd.DataFrame(stg_rows).sample(frac=1, random_state=seed).reset_index(drop=True)
    return {"dim_product": dim, "stg_product": stg}
