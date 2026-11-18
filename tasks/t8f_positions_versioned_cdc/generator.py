import numpy as np
import pandas as pd


def corpus(seed: int):
    """Keys with stale, equal-version and fresh events, version ties ordered by
    batch_seq, zero-quantity closes, deletes then re-inserts, updates with NULL
    price, events for keys with no row, and duplicate delivery."""
    rng = np.random.default_rng(seed)
    syms = ["AAA", "BBB", "CCC", "DDD"]
    target, events = [], []
    seqs = list(rng.permutation(np.arange(1, 2000)))

    def ev(acct, sym, op, ver):
        qty = None if op == "D" else int(rng.choice([0, 5, 10, 25, 40], p=[0.18, 0.2, 0.22, 0.2, 0.2]))
        price = None if (op == "D" or rng.random() < 0.35) else round(float(rng.uniform(5, 300)), 2)
        events.append(dict(batch_seq=int(seqs.pop()), account_id=acct, symbol=sym, op=op, qty=qty,
                           price=price, row_version=int(ver)))

    for acct in range(1, 41):
        for sym in rng.choice(syms, size=int(rng.integers(1, 3)), replace=False):
            ver = int(rng.integers(10, 40))
            target.append(dict(account_id=acct, symbol=str(sym), qty=int(rng.choice([5, 10, 25])),
                               price=None if rng.random() < 0.1 else round(float(rng.uniform(5, 300)), 2),
                               row_version=ver))
            v = ver
            for _ in range(int(rng.integers(0, 5))):
                op = str(rng.choice(["U", "U", "I", "D"]))
                r = rng.random()
                if r < 0.15:
                    ev(acct, str(sym), op, ver)                      # equal to the stored version
                elif r < 0.30:
                    ev(acct, str(sym), op, ver - int(rng.integers(1, 9)))
                else:
                    v += int(rng.integers(0, 3))                     # 0 makes a version tie
                    ev(acct, str(sym), op, max(v, ver + 1))
    for acct in range(100, 125):                                     # keys with no target row
        v = 1
        for op in rng.choice(["I", "U", "D"], size=int(rng.integers(1, 5)), p=[0.45, 0.35, 0.20]):
            v += int(rng.integers(0, 3))
            ev(acct, "ZZZ", str(op), v)
    e = pd.DataFrame(events)
    e = pd.concat([e, e.sample(n=20, random_state=seed)], ignore_index=True).sample(frac=1, random_state=seed + 1).reset_index(drop=True)
    e["qty"] = e["qty"].astype(float)
    e["price"] = e["price"].astype(float)
    t = pd.DataFrame(target)
    t["price"] = t["price"].astype(float)
    return {"target_positions": t, "position_events": e}
