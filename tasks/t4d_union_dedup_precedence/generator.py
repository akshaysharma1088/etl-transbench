import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: for MOST overlapping customers the web row is
    STRICTLY NEWER than the CRM row (recency-first translations pick web —
    wrong); duplicate rows within each source (within-source recency matters);
    exact updated_at ties inside a source with different emails (email ASC
    decides); customers in only one source."""
    rng = np.random.default_rng(seed)
    base = pd.Timestamp("2025-04-01")
    crm_rows, web_rows = [], []
    for cid in range(1, 80):
        in_crm = rng.random() < 0.75
        in_web = rng.random() < 0.75 or not in_crm
        if in_crm:
            k = int(rng.integers(1, 3))
            for _ in range(k):
                crm_rows.append((cid, f"crm{cid}_{rng.integers(0,99)}@ex.com",
                                 base + pd.Timedelta(days=int(rng.integers(0, 20)))))
        if in_web:
            k = int(rng.integers(1, 3))
            for _ in range(k):
                # web rows land LATER on average: recency trap
                web_rows.append((cid, f"web{cid}_{rng.integers(0,99)}@ex.com",
                                 base + pd.Timedelta(days=int(rng.integers(15, 40)))))
    crm = pd.DataFrame(crm_rows, columns=["customer_id", "email", "updated_at"])
    web = pd.DataFrame(web_rows, columns=["customer_id", "email", "updated_at"])
    # exact-timestamp tie inside CRM: email ASC must decide
    tie_ts = base + pd.Timedelta(days=7)
    tie = pd.DataFrame({"customer_id": [500, 500],
                        "email": ["zzz@ex.com", "aaa@ex.com"],
                        "updated_at": [tie_ts, tie_ts]})
    crm = pd.concat([crm, tie], ignore_index=True)
    return {"crm_feed": crm.sample(frac=1, random_state=seed).reset_index(drop=True),
            "web_feed": web.sample(frac=1, random_state=seed + 1).reset_index(drop=True)}
