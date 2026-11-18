"""Executable legacy oracle for t2e_overdraft_fee_cursor."""
import pandas as pd

FEE = 35.00


def run(inputs):
    opening = dict(zip(inputs["accounts"]["account_id"], inputs["accounts"]["opening_balance"]))
    ledger, fees = [], []
    for acct, g in inputs["txns"].sort_values(["account_id", "txn_ts", "txn_id"]).groupby("account_id", sort=True):
        if acct not in opening:
            continue
        bal = round(float(opening[acct]), 2)
        charged = set()
        for t in g.to_dict("records"):
            bal = round(bal + float(t["amount"]), 2)
            day = pd.Timestamp(t["txn_ts"]).normalize()
            if t["amount"] < 0 and bal < 0 and day not in charged:
                bal = round(bal - FEE, 2)
                charged.add(day)
                fees.append(dict(account_id=acct, fee_date=day, trigger_txn_id=t["txn_id"]))
            ledger.append(dict(txn_id=t["txn_id"], balance_after=bal))
    return {"txn_ledger": pd.DataFrame(ledger, columns=["txn_id", "balance_after"]),
            "fees": pd.DataFrame(fees, columns=["account_id", "fee_date", "trigger_txn_id"])}
