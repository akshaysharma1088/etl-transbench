"""Executable legacy oracle for t8e_cdc_ops_replay.
Distinct events by seq, a per-order replay guard on last_seq, then a strict
in-order apply of I/U/D with the NULL-amount-keeps-value rule for updates."""
import pandas as pd


def run(inputs):
    state = {r["order_id"]: dict(r) for r in inputs["target_state"].to_dict("records")}
    guard = {k: v["last_seq"] for k, v in state.items()}
    ev = inputs["cdc_events"].drop_duplicates(subset=["seq"]).sort_values("seq")
    tomb = {}
    for e in ev.to_dict("records"):
        oid = e["order_id"]
        if oid in guard and e["seq"] <= guard[oid]:
            continue
        row = state.get(oid)
        if e["op"] == "D":
            if row is not None:
                del state[oid]
                tomb[oid] = e["seq"]
            continue
        tomb.pop(oid, None)
        if row is None:
            state[oid] = dict(order_id=oid, status=e["status"], amount=e["amount"], last_seq=e["seq"])
        else:
            row["status"] = e["status"]
            if not (e["op"] == "U" and pd.isna(e["amount"])):
                row["amount"] = e["amount"]
            row["last_seq"] = e["seq"]
    new_state = pd.DataFrame(list(state.values()), columns=["order_id", "status", "amount", "last_seq"])
    new_state["amount"] = new_state["amount"].astype(float)
    tombs = pd.DataFrame([dict(order_id=k, deleted_seq=v) for k, v in tomb.items()],
                         columns=["order_id", "deleted_seq"])
    return {"new_state": new_state, "tombstones": tombs}
