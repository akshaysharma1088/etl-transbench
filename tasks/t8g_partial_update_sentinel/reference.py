"""Executable legacy oracle for t8g_partial_update_sentinel."""
import pandas as pd

SENTINEL = "<<NULL>>"
FIELDS = ["email", "phone", "tier"]


def _value(field, v):
    if v == SENTINEL:
        return None
    return str(v).strip().lower() if field == "email" else v


def _same(a, b):
    an, bn = pd.isna(a), pd.isna(b)
    return (an and bn) if (an or bn) else a == b


def run(inputs):
    state = {r["customer_id"]: dict(r) for r in inputs["customer_profile"].to_dict("records")}
    guard = {k: v["updated_seq"] for k, v in state.items()}
    for c in inputs["profile_changes"].sort_values("change_seq").to_dict("records"):
        cid = c["customer_id"]
        if cid in guard and c["change_seq"] <= guard[cid]:
            continue
        row = state.get(cid)
        if row is None:
            state[cid] = dict(customer_id=cid, updated_seq=c["change_seq"],
                              **{f: (None if pd.isna(c[f]) else _value(f, c[f])) for f in FIELDS})
            continue
        changed = False
        for f in FIELDS:
            if pd.isna(c[f]):
                continue
            new = _value(f, c[f])
            if not _same(row[f], new):
                row[f] = new
                changed = True
        if changed:
            row["updated_seq"] = c["change_seq"]
    out = pd.DataFrame(list(state.values()), columns=["customer_id", "email", "phone", "tier", "updated_seq"])
    return {"new_profile": out}
