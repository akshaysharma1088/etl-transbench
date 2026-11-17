import numpy as np
import pandas as pd

def corpus(seed: int):
    """Price lists with several effective dates per SKU, ties on valid_from,
    messy key casing and padding on both sides, future-only prices, SKUs with no
    price, NULL SKUs and quantities, and amounts on the router thresholds."""
    rng = np.random.default_rng(seed)
    skus = [f"SK{i:03d}" for i in range(1, 31)]
    base = pd.Timestamp("2024-03-01")
    prices, lid = [], 1
    for i, sku in enumerate(skus[:26]):                     # SK027..SK030 have no price at all
        offs = sorted(rng.choice(np.arange(-60, 40), size=int(rng.integers(1, 4)), replace=False))
        if i % 6 == 0:
            offs = [25, 35]                                 # only future prices for early orders
        for off in offs:
            n = 2 if rng.random() < 0.3 else 1              # tie on valid_from
            for _ in range(n):
                raw = sku if rng.random() < 0.5 else rng.choice([sku.lower(), " " + sku + " ", sku.title()])
                price = float(rng.choice([0.5, 5.0, 10.0, 12.5, 49.99, 50.0, 100.0, 250.0]))
                prices.append(dict(list_id=lid, sku=raw, unit_price=price, valid_from=base + pd.Timedelta(days=int(off))))
                lid += 1
    prices = pd.DataFrame(prices).sample(frac=1, random_state=seed).reset_index(drop=True)
    prices["list_id"] = rng.permutation(np.arange(1, len(prices) + 1))   # ids unrelated to dates
    orders = []
    for oid in range(1, 401):
        sku = skus[rng.integers(0, 30)]
        r = rng.random()
        raw = None if r < 0.04 else sku if r < 0.5 else rng.choice([sku.lower(), sku + "  ", " " + sku, sku.title()])
        qty = None if rng.random() < 0.06 else float(rng.choice([1, 2, 4, 5, 10, 20, 40, 100, 200]))
        orders.append(dict(order_id=oid, sku=raw, qty=qty,
                           order_date=base + pd.Timedelta(days=int(rng.integers(0, 45)))))
    orders = pd.DataFrame(orders).sample(frac=1, random_state=seed + 1).reset_index(drop=True)
    return {"orders": orders, "price_list": prices}
