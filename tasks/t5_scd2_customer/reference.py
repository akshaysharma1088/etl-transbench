"""Executable legacy oracle for t5_scd2_customer (SCD Type 2)."""
import pandas as pd


def _neq(a, b):
    """Legacy NULL semantics: NULL vs non-NULL is a change; NULL vs NULL is not."""
    an, bn = pd.isna(a), pd.isna(b)
    if an and bn:
        return False
    if an != bn:
        return True
    return a != b


def run(inputs):
    dim = inputs["dim_customer"].copy()
    stg = inputs["stg_customer"].copy()

    # 1. latest staged record per customer; lexicographic (name, segment) tiebreak
    stg = stg.sort_values(
        ["customer_id", "update_date", "name", "segment"],
        ascending=[True, True, True, True], na_position="first"
    ).groupby("customer_id", as_index=False).tail(1)

    rows = dim.to_dict("records")
    for s in stg.to_dict("records"):
        cur_idx = next((i for i, r in enumerate(rows)
                        if r["customer_id"] == s["customer_id"] and r["is_current"] == 1), None)
        if cur_idx is None:
            rows.append(dict(customer_id=s["customer_id"], name=s["name"],
                             segment=s["segment"], eff_start_date=s["update_date"],
                             eff_end_date=pd.NaT, is_current=1))
        else:
            c = rows[cur_idx]
            if _neq(c["name"], s["name"]) or _neq(c["segment"], s["segment"]):
                c["eff_end_date"] = s["update_date"]
                c["is_current"] = 0
                rows.append(dict(customer_id=s["customer_id"], name=s["name"],
                                 segment=s["segment"], eff_start_date=s["update_date"],
                                 eff_end_date=pd.NaT, is_current=1))
            # else: unchanged -> no new version

    out = pd.DataFrame(rows, columns=["customer_id", "name", "segment",
                                      "eff_start_date", "eff_end_date", "is_current"])
    return {"dim_customer_out": out}
