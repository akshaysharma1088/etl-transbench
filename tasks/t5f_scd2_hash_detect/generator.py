import numpy as np
import pandas as pd

CITIES = ["Austin", "Boise", "Chicago", "Denver"]
TIERS = ["GOLD", "SILVER", "BRONZE"]


def corpus(seed: int):
    """Each staged record is built from the member's current row by one named
    mutation, so every quirk of the signature is exercised many times."""
    rng = np.random.default_rng(seed)
    dim, stg = [], []
    start = pd.Timestamp("2023-03-01")
    muts = ["same", "trail_space", "null_to_empty", "empty_to_null", "lead_space", "case",
            "real_city", "real_tier", "delim_shift", "both_null_vs_pipe"]
    for mid in range(1, 121):
        mut = muts[(mid + seed) % len(muts)] if rng.random() < 0.9 else "none"
        city = CITIES[rng.integers(0, 4)]
        tier = TIERS[rng.integers(0, 3)]
        if mut == "null_to_empty":
            tier = None
        if mut == "empty_to_null":
            city = ""
        if mut == "delim_shift":
            city, tier = "A|", "B"
        if mut == "both_null_vs_pipe":
            city, tier = None, None
        dim.append(dict(member_id=mid, city=city, tier=tier, eff_start_date=start,
                        eff_end_date=pd.NaT, is_current=1))
        if mut == "none":
            continue
        s_city, s_tier = city, tier
        if mut == "trail_space":
            s_city, s_tier = city + "  ", tier + " "
        elif mut == "null_to_empty":
            s_tier = ""
        elif mut == "empty_to_null":
            s_city = None
        elif mut == "lead_space":
            s_city = " " + city
        elif mut == "case":
            s_tier = tier.lower()
        elif mut == "real_city":
            s_city = CITIES[(CITIES.index(city) + 1) % 4]
        elif mut == "real_tier":
            s_tier = TIERS[(TIERS.index(tier) + 1) % 3]
        elif mut == "delim_shift":
            s_city, s_tier = "A", "|B"
        elif mut == "both_null_vs_pipe":
            s_city, s_tier = "", None
        stg.append(dict(member_id=mid, city=s_city, tier=s_tier,
                        update_date=pd.Timestamp("2024-06-01") + pd.Timedelta(days=int(rng.integers(0, 60)))))
    for mid in range(500, 506):                       # closed history only, and brand-new members
        dim.append(dict(member_id=mid, city="Austin", tier="GOLD", eff_start_date=start,
                        eff_end_date=pd.Timestamp("2023-09-01"), is_current=0))
        stg.append(dict(member_id=mid, city="Austin", tier="GOLD", update_date=pd.Timestamp("2024-06-15")))
    for mid in range(600, 606):
        stg.append(dict(member_id=mid, city=None if mid % 2 else " Boise ", tier="",
                        update_date=pd.Timestamp("2024-06-20")))
    dim = pd.DataFrame(dim)
    dim["eff_end_date"] = pd.to_datetime(dim["eff_end_date"])
    stg = pd.DataFrame(stg).sample(frac=1, random_state=seed).reset_index(drop=True)
    return {"dim_member": dim, "stg_member": stg}
