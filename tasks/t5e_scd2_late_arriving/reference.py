"""Executable legacy oracle for t5e_scd2_late_arriving.
Staged records are applied one by one in (account_id, update_date) order. A
record dated inside an existing version splits it; one dated before the
account's history is prepended; one dated on a version's start corrects it in
place. The new version inherits the end date and current flag of the version
it was split from."""
import pandas as pd


def _same(a, b):
    an, bn = pd.isna(a), pd.isna(b)
    if an or bn:
        return an and bn
    return a == b


def run(inputs):
    rows = inputs["dim_account"].to_dict("records")
    stg = inputs["stg_account"].sort_values(["account_id", "update_date"])
    for s in stg.to_dict("records"):
        mine = [r for r in rows if r["account_id"] == s["account_id"]]
        d = s["update_date"]
        if not mine:
            rows.append(dict(account_id=s["account_id"], plan=s["plan"], eff_start_date=d,
                             eff_end_date=pd.NaT, is_current=1))
            continue
        v = next((r for r in mine if r["eff_start_date"] <= d
                  and (pd.isna(r["eff_end_date"]) or d < r["eff_end_date"])), None)
        if v is None:
            first = min(mine, key=lambda r: r["eff_start_date"])
            rows.append(dict(account_id=s["account_id"], plan=s["plan"], eff_start_date=d,
                             eff_end_date=first["eff_start_date"], is_current=0))
        elif _same(v["plan"], s["plan"]):
            pass
        elif d == v["eff_start_date"]:
            v["plan"] = s["plan"]
        else:
            rows.append(dict(account_id=s["account_id"], plan=s["plan"], eff_start_date=d,
                             eff_end_date=v["eff_end_date"], is_current=v["is_current"]))
            v["eff_end_date"] = d
            v["is_current"] = 0
    out = pd.DataFrame(rows, columns=["account_id", "plan", "eff_start_date",
                                      "eff_end_date", "is_current"])
    return {"dim_account_out": out}
