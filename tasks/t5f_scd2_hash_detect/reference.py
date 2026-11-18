"""Executable legacy oracle for t5f_scd2_hash_detect.
A change is detected by comparing an unescaped, right-trimmed, NULL-as-empty
concatenation of the tracked columns. Values are stored exactly as staged."""
import pandas as pd


def _part(v):
    return "" if pd.isna(v) else str(v).rstrip(" ")


def _sig(city, tier):
    return _part(city) + "|" + _part(tier)


def run(inputs):
    rows = inputs["dim_member"].to_dict("records")
    current = {r["member_id"]: r for r in rows if r["is_current"] == 1}
    for s in inputs["stg_member"].sort_values("member_id").to_dict("records"):
        c = current.get(s["member_id"])
        if c is not None and _sig(s["city"], s["tier"]) == _sig(c["city"], c["tier"]):
            continue
        if c is not None:
            c["eff_end_date"] = s["update_date"]
            c["is_current"] = 0
        rows.append(dict(member_id=s["member_id"], city=s["city"], tier=s["tier"],
                         eff_start_date=s["update_date"], eff_end_date=pd.NaT, is_current=1))
    out = pd.DataFrame(rows, columns=["member_id", "city", "tier", "eff_start_date",
                                      "eff_end_date", "is_current"])
    return {"dim_member_out": out}
