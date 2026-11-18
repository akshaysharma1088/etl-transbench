import numpy as np
import pandas as pd

AMOUNTS_OK = ["12.50", " 7 ", "+3.5", "100", "0.01", "999999.99", "0010.10"]
AMOUNTS_BAD = ["", "abc", "12.", ".5", "1,000.00", "12.345", "1e3", "$5", "5 USD", "--4", "1 2"]
AMOUNTS_NONPOS = ["0", "0.00", "-3", "-0.5", "+0"]
CUR_OK = ["USD", "eur", " gbp ", "Usd"]
CUR_BAD = ["", "US", "USDX", "JPY", "U SD"]
DATE_OK = ["2024-02-29", "2023-12-31", " 2024-01-05 ", "2024-06-30"]
DATE_BAD = ["2023-02-29", "2024-13-01", "2024-1-5", "01/05/2024", "20240105", "2024-04-31", ""]


def corpus(seed: int):
    """Rows that fail exactly one rule, rows that fail several (only the first
    counts), NULLs in every text column, and duplicate ids arranged so that the
    earliest copy is sometimes itself rejected by an earlier rule."""
    rng = np.random.default_rng(seed)
    pick = lambda xs: xs[rng.integers(0, len(xs))]
    rows = []
    for i in range(1, 321):
        pid = f"P{rng.integers(1, 140):04d}"
        if rng.random() < 0.25:
            pid = pick([" " + pid, pid + " ", pid.lower()])            # padding trims; case does not fold
        row = dict(payment_id=pid, account_id=int(rng.integers(1, 50)), amount_txt=pick(AMOUNTS_OK),
                   currency=pick(CUR_OK), pay_date_txt=pick(DATE_OK))
        for field, bad in (("payment_id", [None, "", "   "]), ("amount_txt", AMOUNTS_BAD + [None]),
                           ("amount_txt", AMOUNTS_NONPOS), ("currency", CUR_BAD + [None]),
                           ("pay_date_txt", DATE_BAD + [None])):
            if rng.random() < 0.09:
                row[field] = pick(bad)
        rows.append(row)
    df = pd.DataFrame(rows).sample(frac=1, random_state=seed).reset_index(drop=True)
    df.insert(0, "row_num", rng.permutation(np.arange(1, len(df) + 1)) * 10)
    return {"raw_payments": df}
