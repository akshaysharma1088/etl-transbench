"""Executable legacy oracle for t8h_inventory_movements."""
import pandas as pd


def run(inputs):
    bal = {(r["sku"], r["warehouse"]): int(r["on_hand"]) for r in inputs["stock_balance"].to_dict("records")}
    applied = list(dict.fromkeys(inputs["applied_movements"]["movement_id"].tolist()))
    seen = set(applied)
    rejects = []
    for m in inputs["movements"].sort_values(["movement_ts", "line_no"]).to_dict("records"):
        if m["movement_id"] in seen:
            continue
        k = (m["sku"], m["warehouse"])
        cur = bal.get(k, 0)
        if cur + int(m["qty"]) < 0:
            rejects.append(dict(line_no=m["line_no"], reason="INSUFFICIENT_STOCK"))
            continue
        bal[k] = cur + int(m["qty"])
        seen.add(m["movement_id"])
        applied.append(m["movement_id"])
    return {"new_balance": pd.DataFrame([dict(sku=k[0], warehouse=k[1], on_hand=v) for k, v in bal.items()],
                                        columns=["sku", "warehouse", "on_hand"]),
            "applied_out": pd.DataFrame({"movement_id": applied}),
            "movement_rejects": pd.DataFrame(rejects, columns=["line_no", "reason"])}
