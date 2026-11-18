"""Executable legacy oracle for t5i_scd2_future_dated."""
import pandas as pd


def run(inputs):
    b = inputs["batch_control"]["batch_date"].iloc[0]
    rows = inputs["dim_price"].to_dict("records")
    by_prod = {}
    for r in rows:
        by_prod.setdefault(r["product_id"], []).append(r)
    for s in inputs["stg_price"].sort_values(["product_id", "effective_date"]).to_dict("records"):
        mine = by_prod.setdefault(s["product_id"], [])
        tail = max(mine, key=lambda r: r["eff_start_date"]) if mine else None
        if tail is not None and float(tail["list_price"]) == float(s["list_price"]):
            continue
        if tail is not None:
            tail["eff_end_date"] = s["effective_date"]
        new = dict(product_id=s["product_id"], list_price=s["list_price"], eff_start_date=s["effective_date"],
                   eff_end_date=pd.NaT, is_current=0)
        mine.append(new)
        rows.append(new)
    for r in rows:
        r["is_current"] = int(r["eff_start_date"] <= b and (pd.isna(r["eff_end_date"]) or b < r["eff_end_date"]))
    out = pd.DataFrame(rows, columns=["product_id", "list_price", "eff_start_date", "eff_end_date", "is_current"])
    return {"dim_price_out": out}
