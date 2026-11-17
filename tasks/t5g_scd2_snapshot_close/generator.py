import numpy as np
import pandas as pd

def corpus(seed: int):
    """Stores that are unchanged, changed, missing from the snapshot (closed),
    previously closed and back (reactivated, some with the same attributes as
    before), previously closed and still absent, and brand new; plus exact
    duplicate snapshot rows and NULL attributes."""
    rng = np.random.default_rng(seed)
    regions = np.array(["N", "S", "E", "W", None], dtype=object)
    formats = np.array(["MALL", "STREET", "OUTLET"], dtype=object)
    batch = pd.Timestamp("2024-09-01") + pd.Timedelta(days=int(rng.integers(0, 30)))
    dim, snap = [], []
    for sid in range(1, 91):
        region, fmt = regions[rng.integers(0, 5)], formats[rng.integers(0, 3)]
        fate = rng.choice(["same", "changed", "gone", "closed_back", "closed_stay"],
                          p=[0.35, 0.25, 0.15, 0.15, 0.10])
        if fate in ("closed_back", "closed_stay"):
            dim.append(dict(store_id=sid, region=region, format=fmt, eff_start_date=pd.Timestamp("2022-01-10"),
                            eff_end_date=pd.Timestamp("2023-04-01"), is_current=0))
            if fate == "closed_back":
                same = rng.random() < 0.6
                snap.append(dict(store_id=sid, region=region if same else "N" if region != "N" else "S", format=fmt))
            continue
        if rng.random() < 0.3:                          # an older closed version as well
            dim.append(dict(store_id=sid, region="W", format="MALL", eff_start_date=pd.Timestamp("2021-06-01"),
                            eff_end_date=pd.Timestamp("2022-01-10"), is_current=0))
        dim.append(dict(store_id=sid, region=region, format=fmt, eff_start_date=pd.Timestamp("2022-01-10"),
                        eff_end_date=pd.NaT, is_current=1))
        if fate == "same":
            snap.append(dict(store_id=sid, region=region, format=fmt))
        elif fate == "changed":
            if rng.random() < 0.5:
                snap.append(dict(store_id=sid, region=None if region is not None else "E", format=fmt))
            else:
                snap.append(dict(store_id=sid, region=region, format=formats[(list(formats).index(fmt) + 1) % 3]))
    for sid in range(400, 408):
        snap.append(dict(store_id=sid, region=regions[rng.integers(0, 5)], format="OUTLET"))
    snap = pd.DataFrame(snap)
    dup = snap.sample(n=12, random_state=seed)        # exact duplicates from the extract
    snap = pd.concat([snap, dup], ignore_index=True).sample(frac=1, random_state=seed + 1).reset_index(drop=True)
    dim = pd.DataFrame(dim)
    dim["eff_end_date"] = pd.to_datetime(dim["eff_end_date"])
    return {"dim_store": dim, "stg_store_full": snap, "batch_control": pd.DataFrame({"batch_date": [batch]})}
