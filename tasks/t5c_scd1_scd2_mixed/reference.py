"""Executable legacy oracle for t5c_scd1_scd2_mixed.
tier is Type-2 (versioned); email is Type-1 (retro-overwritten across all
versions of the key, no versioning). Email-only change touches history rows
but creates no version."""
import pandas as pd

def _neq(a, b):
    an, bn = pd.isna(a), pd.isna(b)
    if an and bn:
        return False
    if an != bn:
        return True
    return a != b

def run(inputs):
    dim = inputs["dim_acct"].copy()
    stg = inputs["stg_acct"].sort_values(
        ["acct_id", "update_date", "email", "tier"],
        ascending=[True, True, True, True], na_position="first"
    ).groupby("acct_id", as_index=False).tail(1)
    rows = dim.to_dict("records")
    for s in stg.to_dict("records"):
        cur_idx = next((i for i, r in enumerate(rows)
                        if r["acct_id"] == s["acct_id"] and r["is_current"] == 1), None)
        if cur_idx is None:
            rows.append(dict(acct_id=s["acct_id"], email=s["email"], tier=s["tier"],
                             eff_start_date=s["update_date"],
                             eff_end_date=pd.NaT, is_current=1))
            continue
        c = rows[cur_idx]
        if _neq(c["tier"], s["tier"]):
            c["eff_end_date"] = s["update_date"]
            c["is_current"] = 0
            rows.append(dict(acct_id=s["acct_id"], email=s["email"], tier=s["tier"],
                             eff_start_date=s["update_date"],
                             eff_end_date=pd.NaT, is_current=1))
        if _neq(c["email"], s["email"]):
            for r in rows:
                if r["acct_id"] == s["acct_id"]:
                    r["email"] = s["email"]
    out = pd.DataFrame(rows, columns=["acct_id", "email", "tier",
                                      "eff_start_date", "eff_end_date", "is_current"])
    return {"dim_acct_out": out}
