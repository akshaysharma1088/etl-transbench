import numpy as np
import pandas as pd


def corpus(seed: int):
    """Keys that are unchanged, changed in one or several columns, changed only
    by trailing spaces (not a change), by leading spaces or case (a change),
    NULL to value and back, integer stock stored as float, inserted and deleted."""
    rng = np.random.default_rng(seed)
    prev, curr = [], []
    for i in range(1, 181):
        key = dict(region=str(rng.choice(["EU", "US", "APAC"])), sku=f"S{i:04d}")
        p = dict(price=None if rng.random() < 0.1 else round(float(rng.uniform(1, 90)), 2),
                 stock=None if rng.random() < 0.1 else float(rng.integers(0, 50)),
                 label=None if rng.random() < 0.1 else str(rng.choice(["Basic", "Promo", "", "New item"])))
        c = dict(p)
        fate = rng.choice(["same", "pad", "lead", "case", "price", "stock", "null", "multi", "ins", "del", "blank"],
                          p=[0.2, 0.1, 0.07, 0.07, 0.1, 0.1, 0.1, 0.1, 0.06, 0.06, 0.04])
        if fate == "pad" and p["label"] is not None:
            c["label"] = p["label"] + "   "
        elif fate == "lead" and p["label"]:
            c["label"] = " " + p["label"]
        elif fate == "case" and p["label"]:
            c["label"] = p["label"].upper()
        elif fate == "price":
            c["price"] = round(float(rng.uniform(1, 90)), 2)
        elif fate == "stock":
            c["stock"] = float(rng.integers(50, 99))
        elif fate == "null":
            f = str(rng.choice(["price", "stock", "label"]))
            c[f] = None if p[f] is not None else {"price": 9.99, "stock": 7.0, "label": "Basic"}[f]
        elif fate == "multi":
            c["price"] = round(float(rng.uniform(100, 200)), 2)
            c["label"] = "Relabelled"
        elif fate == "blank":
            p["label"], c["label"] = "  ", ""
        if fate != "ins":
            prev.append({**key, **p})
        if fate != "del":
            curr.append({**key, **c})
    mk = lambda rows, s: pd.DataFrame(rows).sample(frac=1, random_state=s).reset_index(drop=True)
    return {"snap_prev": mk(prev, seed), "snap_curr": mk(curr, seed + 1)}
