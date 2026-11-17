"""Executable legacy oracle for t7e_shortcircuit_parse_dedupe.
Rules run in a fixed order and stop at the first failure. The number and date
parsers accept only the legacy formats. Duplicates are decided last, among the
rows that survived, by lowest row_num."""
import re
import pandas as pd

NUM = re.compile(r"[+-]?[0-9]+(\.[0-9]{1,2})?")
DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def _trim(v):
    return None if pd.isna(v) else str(v).strip(" ")


def run(inputs):
    raw = inputs["raw_payments"].sort_values("row_num")
    valid, rejects, seen = [], [], set()
    for r in raw.to_dict("records"):
        pid, amt, cur, dt = (_trim(r["payment_id"]), _trim(r["amount_txt"]),
                             _trim(r["currency"]), _trim(r["pay_date_txt"]))
        reason, amount, day = None, None, None
        if not pid:
            reason = "MISSING_ID"
        elif amt is None or not NUM.fullmatch(amt):
            reason = "BAD_AMOUNT"
        else:
            amount = float(amt)
            if amount <= 0:
                reason = "NON_POSITIVE"
            elif cur is None or cur.upper() not in ("USD", "EUR", "GBP"):
                reason = "BAD_CURRENCY"
            else:
                day = pd.to_datetime(dt, format="%Y-%m-%d", errors="coerce") if dt and DATE.fullmatch(dt) else pd.NaT
                if pd.isna(day):
                    reason = "BAD_DATE"
                elif pid in seen:
                    reason = "DUPLICATE"
        if reason:
            rejects.append(dict(row_num=r["row_num"], reject_reason=reason))
        else:
            seen.add(pid)
            valid.append(dict(payment_id=pid, account_id=r["account_id"], amount=amount,
                              currency=cur.upper(), pay_date=day))
    return {"valid_payments": pd.DataFrame(valid, columns=["payment_id", "account_id", "amount",
                                                           "currency", "pay_date"]),
            "payment_rejects": pd.DataFrame(rejects, columns=["row_num", "reject_reason"])}
