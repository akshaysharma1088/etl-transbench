"""Executable legacy oracle for t7f_running_limit_validation."""
import pandas as pd


def run(inputs):
    limit = dict(zip(inputs["account_limits"]["account_id"], inputs["account_limits"]["daily_limit"]))
    refs, totals, ok, bad = set(), {}, [], []
    for r in inputs["transfers"].sort_values("row_num").to_dict("records"):
        reason = None
        key = (r["account_id"], r["transfer_date"])
        if r["account_id"] not in limit:
            reason = "UNKNOWN_ACCOUNT"
        elif pd.isna(r["amount"]) or r["amount"] <= 0:
            reason = "BAD_AMOUNT"
        elif r["transfer_ref"] in refs:
            reason = "DUPLICATE_REF"
        elif round(totals.get(key, 0.0) + float(r["amount"]), 2) > float(limit[r["account_id"]]):
            reason = "OVER_LIMIT"
        if reason:
            bad.append(dict(row_num=r["row_num"], reason=reason))
            continue
        refs.add(r["transfer_ref"])
        totals[key] = round(totals.get(key, 0.0) + float(r["amount"]), 2)
        ok.append(dict(row_num=r["row_num"], account_id=r["account_id"], amount=float(r["amount"]),
                       running_total=totals[key]))
    return {"accepted_transfers": pd.DataFrame(ok, columns=["row_num", "account_id", "amount", "running_total"]),
            "transfer_rejects": pd.DataFrame(bad, columns=["row_num", "reason"])}
