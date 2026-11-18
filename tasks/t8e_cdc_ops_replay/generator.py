import numpy as np
import pandas as pd

def corpus(seed: int):
    """Orders with stale and fresh events around their last_seq, delete then
    re-insert chains, updates with NULL amounts (keep the value), inserts for
    existing rows, updates and deletes for missing rows, duplicate delivery, and
    event timestamps that disagree with seq."""
    rng = np.random.default_rng(seed)
    statuses = ["NEW", "PAID", "SHIPPED", "HOLD"]
    target, events = [], []
    seq = 1000
    seqs = list(rng.permutation(np.arange(1001, 1001 + 900)))
    def ev(oid, op, s=None):
        s = int(seqs.pop()) if s is None else s
        amount = None if (op == "D" or rng.random() < 0.35) else round(float(rng.uniform(5, 500)), 2)
        events.append(dict(seq=s, order_id=oid, op=op, status=None if op == "D" else statuses[rng.integers(0, 4)],
                           amount=amount,
                           event_ts=pd.Timestamp("2024-04-01") + pd.Timedelta(minutes=int(rng.integers(0, 5000)))))
    for oid in range(1, 81):
        last = int(rng.integers(1100, 1700))
        target.append(dict(order_id=oid, status=statuses[rng.integers(0, 4)],
                           amount=None if rng.random() < 0.1 else round(float(rng.uniform(5, 500)), 2), last_seq=last))
        for _ in range(int(rng.integers(0, 5))):
            op = str(rng.choice(["U", "U", "I", "D"]))
            r = rng.random()
            if r < 0.15:
                ev(oid, op, last)                              # equal to last_seq: a replay
            elif r < 0.35:
                ev(oid, op, int(last - rng.integers(1, 90)))   # older than last_seq
            else:
                ev(oid, op)
    for oid in range(200, 240):                               # orders with no target row
        for op in rng.choice(["I", "U", "D"], size=int(rng.integers(1, 5)), p=[0.45, 0.35, 0.20]):
            ev(oid, str(op))
    ev_df = pd.DataFrame(events).drop_duplicates(subset=["seq"])
    dup = ev_df.sample(n=min(25, len(ev_df)), random_state=seed)      # at-least-once delivery
    ev_df = pd.concat([ev_df, dup], ignore_index=True).sample(frac=1, random_state=seed + 1).reset_index(drop=True)
    ev_df["amount"] = ev_df["amount"].astype(float)
    tgt = pd.DataFrame(target)
    tgt["amount"] = tgt["amount"].astype(float)
    return {"target_state": tgt, "cdc_events": ev_df}
