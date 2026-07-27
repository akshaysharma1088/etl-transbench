import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def corpus(seed: int):
    rng = np.random.default_rng(seed)
    n_dim, n_stg = 60, 80
    segs = np.array(["RETAIL", "PREMIER", "PRIVATE", None], dtype=object)

    # existing dimension: one current row per customer 1..n_dim, some with history
    dim_rows = []
    for cid in range(1, n_dim + 1):
        name = f"CUST_{cid:04d}_V1"
        seg = segs[rng.integers(0, len(segs))]
        start = pd.Timestamp("2023-01-01") + pd.Timedelta(days=int(rng.integers(0, 200)))
        if rng.random() < 0.3:  # prior expired version
            dim_rows.append(dict(customer_id=cid, name=f"CUST_{cid:04d}_V0",
                                 segment="RETAIL", eff_start_date=start - pd.Timedelta(days=400),
                                 eff_end_date=start, is_current=0))
        dim_rows.append(dict(customer_id=cid, name=name, segment=seg,
                             eff_start_date=start, eff_end_date=pd.NaT, is_current=1))
    dim = pd.DataFrame(dim_rows)

    # staging: mix of changed / unchanged / brand-new / duplicate-per-key
    stg_rows = []
    for _ in range(n_stg):
        cid = int(rng.integers(1, n_dim + 25))            # some beyond n_dim => new
        upd = pd.Timestamp("2024-06-01") + pd.Timedelta(days=int(rng.integers(0, 120)))
        cur = dim[(dim.customer_id == cid) & (dim.is_current == 1)]
        r = rng.random()
        if len(cur) and r < 0.35:                          # unchanged record probe
            stg_rows.append(dict(customer_id=cid, name=cur.iloc[0]["name"],
                                 segment=cur.iloc[0]["segment"], update_date=upd))
        else:                                              # changed or new
            stg_rows.append(dict(customer_id=cid, name=f"CUST_{cid:04d}_V{int(rng.integers(2, 9))}",
                                 segment=segs[rng.integers(0, len(segs))], update_date=upd))
    # duplicate staged keys with identical update_date to exercise the tiebreak
    for i in range(5):
        base = dict(stg_rows[i])
        base["name"] = base["name"] + "_DUP"
        stg_rows.append(base)
    stg = pd.DataFrame(stg_rows)
    return {"dim_customer": dim, "stg_customer": stg}
