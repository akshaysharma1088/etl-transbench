import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: STMT rows carry NONZERO fees (so reset-order
    bugs shift a real amount between cycles); STMT rows share entry_date with
    surrounding TXN rows (date-tie + row_seq break); physical order shuffled;
    some accounts BEGIN with a STMT row (cycle numbering edge)."""
    rng = np.random.default_rng(seed)
    n = 400
    df = pd.DataFrame({
        "account_id": rng.integers(1, 30, n),
        "row_seq": np.arange(1, n + 1),
        "entry_date": pd.Timestamp("2025-03-01")
                      + pd.to_timedelta(rng.integers(0, 60, n), unit="D"),
        "entry_type": np.where(rng.random(n) < 0.12, "STMT", "TXN"),
        "amount": rng.uniform(-400, 400, n),
    })
    df.loc[df["entry_type"] == "STMT", "amount"] = -rng.uniform(5, 40, (df["entry_type"] == "STMT").sum())
    df.loc[rng.random(n) < 0.05, "amount"] = np.nan
    # ties: STMT + TXN same account/date, row_seq decides order
    stmt_rows = df[df["entry_type"] == "STMT"].head(10)
    ties = stmt_rows.copy()
    ties["entry_type"] = "TXN"
    ties["row_seq"] = ties["row_seq"] + 10_000
    ties["amount"] = rng.uniform(50, 150, len(ties))
    # account that begins with a STMT row
    lead = pd.DataFrame({
        "account_id": [999], "row_seq": [1],
        "entry_date": [pd.Timestamp("2025-03-01")],
        "entry_type": ["STMT"], "amount": [-25.0],
    })
    out = pd.concat([df, ties, lead], ignore_index=True)
    return {"ledger": out.sample(frac=1, random_state=seed).reset_index(drop=True)}
