"""Executable legacy oracle for t2f_fifo_lot_matching."""
import pandas as pd


def run(inputs):
    sells, lots_out = [], []
    tr = inputs["trades"].sort_values(["account_id", "symbol", "trade_ts", "trade_id"])
    for (acct, sym), g in tr.groupby(["account_id", "symbol"], sort=True):
        lots = []
        for t in g.to_dict("records"):
            if t["side"] == "BUY":
                lots.append(dict(lot_trade_id=t["trade_id"], account_id=acct, symbol=sym,
                                 remaining_qty=int(t["qty"]), price=float(t["price"])))
                continue
            need, pnl = int(t["qty"]), 0.0
            for lot in lots:
                if need == 0:
                    break
                take = min(lot["remaining_qty"], need)
                pnl += take * (float(t["price"]) - lot["price"])
                lot["remaining_qty"] -= take
                need -= take
            sells.append(dict(trade_id=t["trade_id"], matched_qty=int(t["qty"]) - need, short_qty=need,
                              realized_pnl=round(pnl, 2)))
        lots_out += [l for l in lots if l["remaining_qty"] > 0]
    return {"sell_results": pd.DataFrame(sells, columns=["trade_id", "matched_qty", "short_qty", "realized_pnl"]),
            "open_lots": pd.DataFrame(lots_out, columns=["lot_trade_id", "account_id", "symbol",
                                                         "remaining_qty", "price"])}
