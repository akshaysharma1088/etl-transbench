import numpy as np
import pandas as pd


def corpus(seed: int):
    """Payments that span several invoices, exact pay-offs, overpayments, shared
    due dates ordered by invoice_id, payments at the same instant ordered by
    payment_id, customers with no invoices and customers with no payments."""
    rng = np.random.default_rng(seed)
    inv, pay = [], []
    base = pd.Timestamp("2024-01-01")
    amounts = [25.0, 40.0, 50.0, 75.25, 100.0, 150.5, 200.0, 400.0]
    for c in range(1, 46):
        for _ in range(int(rng.integers(0, 6)) if c % 9 else 0):
            inv.append(dict(customer_id=c, due_date=base + pd.Timedelta(days=int(rng.choice([10, 10, 20, 30, 45, 60]))),
                            amount=float(rng.choice(amounts))))
        for _ in range(int(rng.integers(0, 5)) if c % 7 else 0):
            pay.append(dict(customer_id=c, paid_ts=base + pd.Timedelta(days=int(rng.integers(1, 6)), hours=int(rng.choice([9, 9, 14]))),
                            amount=float(rng.choice(amounts + [600.0, 25.0, 50.0]))))
    i = pd.DataFrame(inv).sample(frac=1, random_state=seed).reset_index(drop=True)
    i.insert(0, "invoice_id", rng.permutation(np.arange(1000, 1000 + len(i))))
    p = pd.DataFrame(pay).sample(frac=1, random_state=seed + 1).reset_index(drop=True)
    p.insert(0, "payment_id", rng.permutation(np.arange(5000, 5000 + len(p))))
    return {"invoices": i, "payments": p}
