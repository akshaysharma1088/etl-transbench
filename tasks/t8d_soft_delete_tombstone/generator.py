import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import numpy as np
import pandas as pd

def corpus(seed: int):
    """Adversarial construction: D-then-U chains where the U lands INSIDE the
    7-day window (discard — hard-delete or plain-upsert translations resurrect
    wrongly), EXACTLY at 7 days (still sticky: strict >), and just past it
    (resurrect); pre-existing DELETED snapshot rows whose window spans the
    batch; U-after-resurrection chains; email preserved on delete."""
    rng = np.random.default_rng(seed)
    wm = pd.Timestamp("2025-07-01 00:00:00")
    snap_rows, evs = [], []
    seq = 1
    def ev(uid, op, email, ts):
        nonlocal seq
        evs.append(dict(event_seq=seq, event_ts=ts, op=op,
                        user_id=uid, email=email))
        seq += 1
    for uid in range(1, 35):
        deleted = rng.random() < 0.3
        snap_rows.append(dict(
            user_id=uid, email=f"u{uid}@old.com",
            status="DELETED" if deleted else "ACTIVE",
            status_ts=wm - pd.Timedelta(days=int(rng.integers(1, 12))) if deleted
                      else wm - pd.Timedelta(days=30)))
    t0 = wm + pd.Timedelta(hours=2)
    for uid in range(1, 30):
        pat = rng.choice(["DU_in", "DU_edge", "DU_out", "U", "D", "UDU"])
        if pat == "DU_in":
            d = t0 + pd.Timedelta(hours=int(rng.integers(0, 24)))
            ev(uid, "D", None, d)
            ev(uid, "U", f"u{uid}@new.com", d + pd.Timedelta(days=3))
        elif pat == "DU_edge":
            d = t0
            ev(uid, "D", None, d)
            ev(uid, "U", f"u{uid}@edge.com", d + pd.Timedelta(days=7))       # sticky
        elif pat == "DU_out":
            d = t0
            ev(uid, "D", None, d)
            ev(uid, "U", f"u{uid}@back.com",
               d + pd.Timedelta(days=7, seconds=1))                          # resurrect
        elif pat == "U":
            ev(uid, "U", f"u{uid}@upd.com", t0 + pd.Timedelta(hours=uid))
        elif pat == "D":
            ev(uid, "D", None, t0 + pd.Timedelta(hours=uid))
        else:  # UDU
            ev(uid, "U", f"u{uid}@a.com", t0)
            ev(uid, "D", None, t0 + pd.Timedelta(days=1))
            ev(uid, "U", f"u{uid}@b.com", t0 + pd.Timedelta(days=9))         # resurrect
    ev(600, "U", "new600@ex.com", t0)                    # brand-new user
    snap = pd.DataFrame(snap_rows)
    events = pd.DataFrame(evs).sample(frac=1, random_state=seed).reset_index(drop=True)
    return {"target_snapshot": snap, "cdc_events": events,
            "watermark": pd.DataFrame({"high_ts": [wm]})}
