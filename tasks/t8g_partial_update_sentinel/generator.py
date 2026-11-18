import numpy as np
import pandas as pd


def corpus(seed: int):
    """Changes that touch one field, several fields, or none; sentinels on NULL
    and non-NULL fields; emails that differ only in case or padding (a no-op);
    stale changes; no-op changes after the last real one; new customers."""
    rng = np.random.default_rng(seed)
    tiers = ["BASIC", "PLUS", "PRO"]
    prof, chg = [], []
    seqs = list(rng.permutation(np.arange(1, 3000)))
    for cid in range(1, 91):
        useq = int(rng.integers(100, 1500))
        email = None if rng.random() < 0.15 else f"user{cid}@example.com"
        phone = None if rng.random() < 0.3 else f"555-{cid:04d}"
        tier = None if rng.random() < 0.1 else tiers[rng.integers(0, 3)]
        prof.append(dict(customer_id=cid, email=email, phone=phone, tier=tier, updated_seq=useq))
        for _ in range(int(rng.integers(0, 5))):
            r = rng.random()
            seq = useq if r < 0.1 else useq - int(rng.integers(1, 90)) if r < 0.25 else useq + int(rng.integers(1, 1400))
            row = dict(change_seq=None, customer_id=cid, email=None, phone=None, tier=None)
            kind = rng.choice(["email_same", "email_new", "phone", "tier", "sentinel", "empty", "multi", "tier_same"])
            if kind == "email_same" and email:
                row["email"] = rng.choice([email.upper(), "  " + email + " ", email])
            elif kind == "email_new":
                row["email"] = f" New{cid}.{int(rng.integers(0, 9))}@Example.COM "
            elif kind == "phone":
                row["phone"] = f"555-{int(rng.integers(0, 9999)):04d}"
            elif kind == "tier":
                row["tier"] = tiers[rng.integers(0, 3)]
            elif kind == "tier_same" and tier:
                row["tier"] = tier
            elif kind == "sentinel":
                row[str(rng.choice(["email", "phone", "tier"]))] = "<<NULL>>"
            elif kind == "multi":
                row["phone"] = "<<NULL>>" if rng.random() < 0.4 else f"555-{int(rng.integers(0, 9999)):04d}"
                row["tier"] = tiers[rng.integers(0, 3)]
            row["change_seq"] = seq
            chg.append(row)
    for cid in range(300, 316):
        for j in range(int(rng.integers(1, 4))):
            chg.append(dict(change_seq=None, customer_id=cid,
                            email=None if rng.random() < 0.4 else f"NEW{cid}@Example.com",
                            phone="<<NULL>>" if rng.random() < 0.3 else None,
                            tier=None if rng.random() < 0.5 else tiers[rng.integers(0, 3)]))
            chg[-1]["change_seq"] = 2000 + cid * 3 + j
    c = pd.DataFrame(chg).sample(frac=1, random_state=seed).reset_index(drop=True)
    # change_seq must be unique: spread collisions deterministically
    c = c.sort_values("change_seq", kind="stable").reset_index(drop=True)
    c["change_seq"] = c["change_seq"] * 10 + c.groupby("change_seq").cumcount()
    p = pd.DataFrame(prof)
    p["updated_seq"] = p["updated_seq"] * 10
    return {"customer_profile": p, "profile_changes": c.sample(frac=1, random_state=seed + 1).reset_index(drop=True)}
