"""Executable legacy oracle for t8f_positions_versioned_cdc."""
import pandas as pd


def run(inputs):
    state = {(r["account_id"], r["symbol"]): dict(r) for r in inputs["target_positions"].to_dict("records")}
    guard = {k: v["row_version"] for k, v in state.items()}
    ev = (inputs["position_events"].drop_duplicates(subset=["batch_seq"])
          .sort_values(["row_version", "batch_seq"]))
    closed = {}
    for e in ev.to_dict("records"):
        k = (e["account_id"], e["symbol"])
        if k in guard and e["row_version"] <= guard[k]:
            continue
        row = state.get(k)
        if e["op"] == "D" or e["qty"] == 0:
            if row is not None:
                del state[k]
                closed[k] = e["row_version"]
            continue
        closed.pop(k, None)
        if row is None:
            state[k] = dict(account_id=k[0], symbol=k[1], qty=e["qty"], price=e["price"],
                            row_version=e["row_version"])
        else:
            row["qty"] = e["qty"]
            if not (e["op"] == "U" and pd.isna(e["price"])):
                row["price"] = e["price"]
            row["row_version"] = e["row_version"]
    out = pd.DataFrame(list(state.values()), columns=["account_id", "symbol", "qty", "price", "row_version"])
    out["price"] = out["price"].astype(float)
    out["qty"] = out["qty"].astype(float)
    cl = pd.DataFrame([dict(account_id=k[0], symbol=k[1], closed_version=v) for k, v in closed.items()],
                      columns=["account_id", "symbol", "closed_version"])
    return {"new_positions": out, "closed_positions": cl}
