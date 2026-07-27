"""Executable legacy oracle for t5b_scd2_multi_batch.
SCD2 applied SEQUENTIALLY over every staged record in update_date order —
no dedup-to-latest. Intermediate versions from multi-update batches appear
in history."""
import pandas as pd

def _neq(a, b):
    an, bn = pd.isna(a), pd.isna(b)
    if an and bn:
        return False
    if an != bn:
        return True
    return a != b

def run(inputs):
    dim = inputs["dim_product"].copy()
    stg = inputs["stg_product"].sort_values(
        ["product_id", "update_date"]).copy()
    rows = dim.to_dict("records")
    for s in stg.to_dict("records"):
        cur_idx = next((i for i, r in enumerate(rows)
                        if r["product_id"] == s["product_id"]
                        and r["is_current"] == 1), None)
        if cur_idx is None:
            rows.append(dict(product_id=s["product_id"], category=s["category"],
                             price_band=s["price_band"],
                             eff_start_date=s["update_date"],
                             eff_end_date=pd.NaT, is_current=1))
        else:
            c = rows[cur_idx]
            if _neq(c["category"], s["category"]) or _neq(c["price_band"], s["price_band"]):
                c["eff_end_date"] = s["update_date"]
                c["is_current"] = 0
                rows.append(dict(product_id=s["product_id"], category=s["category"],
                                 price_band=s["price_band"],
                                 eff_start_date=s["update_date"],
                                 eff_end_date=pd.NaT, is_current=1))
    out = pd.DataFrame(rows, columns=["product_id", "category", "price_band",
                                      "eff_start_date", "eff_end_date", "is_current"])
    return {"dim_product_out": out}
