import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: dense MULTI-FAILURE rows (first-match
    translations emit only the first code); rows where R3 would compare
    against NULL (NULL-safety probe); whitespace-only customer_ref; boundary
    tax == amount*0.5 exactly (passes R3); negative-zero amounts."""
    rng = np.random.default_rng(seed)
    n = 400
    df = pd.DataFrame({
        "invoice_id": np.arange(1, n + 1),
        "amount": rng.uniform(-200, 2000, n).round(2),
        "tax": rng.uniform(-50, 900, n).round(2),
        "due_date": pd.Timestamp("2025-07-01")
                    + pd.to_timedelta(rng.integers(0, 60, n), unit="D"),
        "customer_ref": [f"C{int(x):05d}" for x in rng.integers(1, 9000, n)],
    })
    m = rng.random(n)
    df.loc[m < 0.08, "amount"] = np.nan
    df.loc[(m >= 0.08) & (m < 0.14), "tax"] = np.nan
    df.loc[(m >= 0.14) & (m < 0.20), "due_date"] = pd.NaT
    df.loc[(m >= 0.20) & (m < 0.24), "customer_ref"] = "   "
    df.loc[(m >= 0.24) & (m < 0.27), "customer_ref"] = None
    # dense multi-failure rows: everything wrong at once
    multi = pd.DataFrame({
        "invoice_id": np.arange(9001, 9016),
        "amount": [-10.0] * 15, "tax": [-5.0] * 15,
        "due_date": [pd.NaT] * 15, "customer_ref": [""] * 15,
    })
    # exact boundary: tax == amount * 0.5 passes R3
    edge = pd.DataFrame({
        "invoice_id": [9501, 9502],
        "amount": [100.0, 100.0], "tax": [50.0, 50.01],
        "due_date": [pd.Timestamp("2025-07-15")] * 2,
        "customer_ref": ["C11111", "C22222"],
    })
    out = pd.concat([df, multi, edge], ignore_index=True)
    return {"invoices": out.sample(frac=1, random_state=seed).reset_index(drop=True)}
