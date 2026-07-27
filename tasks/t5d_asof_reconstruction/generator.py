import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: contiguous version chains per employee where
    each version's end equals the next version's start, and A LARGE SHARE OF
    QUERIES LAND EXACTLY ON BOUNDARY DATES — end-inclusive translations match
    TWO versions there (duplicate query_id rows), start-exclusive translations
    match none; queries before first version, after last (NULL-end current),
    and for unknown employees included."""
    rng = np.random.default_rng(seed)
    hist_rows, q_rows = [], []
    qid = 1
    boundaries = {}
    for emp in range(1, 60):
        k = int(rng.integers(1, 5))
        starts = pd.Timestamp("2022-01-01") + pd.to_timedelta(
            np.sort(rng.choice(np.arange(0, 1000), size=k, replace=False)), unit="D")
        emp_bounds = []
        for j, s in enumerate(starts):
            end = starts[j + 1] if j + 1 < k else pd.NaT
            hist_rows.append(dict(emp_id=emp,
                                  dept=str(rng.choice(["ENG", "OPS", "FIN"])),
                                  grade=str(rng.choice(["G1", "G2", "G3", "G4"])),
                                  eff_start_date=s, eff_end_date=end,
                                  is_current=int(j + 1 == k)))
            emp_bounds.append(s)
        boundaries[emp] = emp_bounds
        for _ in range(int(rng.integers(1, 4))):
            r = rng.random()
            if r < 0.45 and len(emp_bounds) > 1:          # exact boundary date
                d = emp_bounds[int(rng.integers(1, len(emp_bounds)))]
            elif r < 0.60:                                # before first version
                d = emp_bounds[0] - pd.Timedelta(days=int(rng.integers(1, 100)))
            elif r < 0.75:                                # far future (NULL-end row)
                d = pd.Timestamp("2026-06-01")
            else:                                         # mid-interval
                d = emp_bounds[0] + pd.Timedelta(days=int(rng.integers(1, 30)))
            q_rows.append(dict(query_id=qid, emp_id=emp, as_of_date=d))
            qid += 1
    for _ in range(10):                                   # unknown employees
        q_rows.append(dict(query_id=qid, emp_id=int(rng.integers(900, 950)),
                           as_of_date=pd.Timestamp("2024-01-01")))
        qid += 1
    hist = pd.DataFrame(hist_rows).sample(frac=1, random_state=seed).reset_index(drop=True)
    queries = pd.DataFrame(q_rows).sample(frac=1, random_state=seed + 1).reset_index(drop=True)
    return {"dim_emp_hist": hist, "asof_queries": queries}
