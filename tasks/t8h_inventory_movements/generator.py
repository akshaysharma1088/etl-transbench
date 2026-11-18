import numpy as np
import pandas as pd


def corpus(seed: int):
    """Outbound lines that overdraw until a later inbound arrives, redelivered
    movement ids (after an apply and after a reject), ids applied by earlier
    runs, keys with no balance row, and timestamp ties broken by line_no."""
    rng = np.random.default_rng(seed)
    skus = [f"SKU{i:02d}" for i in range(1, 15)]
    whs = ["W1", "W2"]
    bal = [dict(sku=s, warehouse=w, on_hand=int(rng.choice([0, 3, 10, 40])))
           for s in skus[:11] for w in whs if rng.random() < 0.8]
    prior = [f"M{i:04d}" for i in range(1, 16)]
    base = pd.Timestamp("2024-08-01 06:00:00")
    lines, mid = [], 100
    for _ in range(170):
        r = rng.random()
        if r < 0.10:
            m = str(rng.choice(prior))                       # applied by an earlier run
        elif r < 0.28 and lines:
            m = lines[int(rng.integers(0, len(lines)))]["movement_id"]   # redelivery
        else:
            mid += 1
            m = f"M{mid:04d}"
        prev = next((l for l in lines if l["movement_id"] == m), None)
        sku, wh = (prev["sku"], prev["warehouse"]) if prev else (str(rng.choice(skus)), str(rng.choice(whs)))
        qty = prev["qty"] if prev else int(rng.choice([-30, -12, -5, -1, 4, 9, 20, 35]))
        ts = base + pd.Timedelta(minutes=int(rng.integers(0, 60)) * 5)   # many ties
        lines.append(dict(movement_id=m, sku=sku, warehouse=wh, qty=qty, movement_ts=ts))
    df = pd.DataFrame(lines).sample(frac=1, random_state=seed).reset_index(drop=True)
    df.insert(0, "line_no", rng.permutation(np.arange(1, len(df) + 1)))
    return {"stock_balance": pd.DataFrame(bal), "applied_movements": pd.DataFrame({"movement_id": prior}),
            "movements": df}
