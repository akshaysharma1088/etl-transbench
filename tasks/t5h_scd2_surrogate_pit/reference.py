"""Executable legacy oracle for t5h_scd2_surrogate_pit.
Step 1 versions the dimension and numbers new rows from MAX(sk) in customer_id
order. Step 2 resolves each fact to the version valid on its date, with an
exclusive end date and -1 when nothing matches."""
import pandas as pd


def _differs(a, b):
    an, bn = pd.isna(a), pd.isna(b)
    if an or bn:
        return an != bn
    return a != b


def run(inputs):
    rows = inputs["dim_customer"].to_dict("records")
    next_sk = int(inputs["dim_customer"]["customer_sk"].max())
    current = {r["customer_id"]: r for r in rows if r["is_current"] == 1}
    for s in inputs["stg_customer"].sort_values("customer_id").to_dict("records"):
        c = current.get(s["customer_id"])
        if c is not None and not _differs(c["segment"], s["segment"]):
            continue
        if c is not None:
            c["eff_end_date"] = s["update_date"]
            c["is_current"] = 0
        next_sk += 1
        rows.append(dict(customer_sk=next_sk, customer_id=s["customer_id"], segment=s["segment"],
                         eff_start_date=s["update_date"], eff_end_date=pd.NaT, is_current=1))
    dim = pd.DataFrame(rows, columns=["customer_sk", "customer_id", "segment", "eff_start_date",
                                      "eff_end_date", "is_current"])
    by_cust = {}
    for r in rows:
        by_cust.setdefault(r["customer_id"], []).append(r)
    keyed = []
    for f in inputs["fact_txn"].to_dict("records"):
        sk = -1
        for r in by_cust.get(f["customer_id"], []):
            if r["eff_start_date"] <= f["txn_date"] and (pd.isna(r["eff_end_date"])
                                                         or f["txn_date"] < r["eff_end_date"]):
                sk = r["customer_sk"]
                break
        keyed.append(dict(txn_id=f["txn_id"], customer_sk=sk, amount=f["amount"]))
    return {"dim_customer_out": dim,
            "fact_txn_keyed": pd.DataFrame(keyed, columns=["txn_id", "customer_sk", "amount"])}
