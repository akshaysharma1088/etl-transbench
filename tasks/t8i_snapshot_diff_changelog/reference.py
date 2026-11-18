"""Executable legacy oracle for t8i_snapshot_diff_changelog."""
import pandas as pd


def _differs(col, a, b):
    an, bn = pd.isna(a), pd.isna(b)
    if an or bn:
        return an != bn
    if col == "label":
        return str(a).rstrip(" ") != str(b).rstrip(" ")
    return float(a) != float(b)


def run(inputs):
    prev = {(r["region"], r["sku"]): r for r in inputs["snap_prev"].to_dict("records")}
    curr = {(r["region"], r["sku"]): r for r in inputs["snap_curr"].to_dict("records")}
    rows = []
    for k in sorted(set(prev) | set(curr)):
        if k not in prev:
            rows.append(dict(region=k[0], sku=k[1], change_type="I", changed_cols=None))
        elif k not in curr:
            rows.append(dict(region=k[0], sku=k[1], change_type="D", changed_cols=None))
        else:
            cols = [c for c in ("price", "stock", "label") if _differs(c, prev[k][c], curr[k][c])]
            if cols:
                rows.append(dict(region=k[0], sku=k[1], change_type="U", changed_cols=",".join(cols)))
    return {"change_log": pd.DataFrame(rows, columns=["region", "sku", "change_type", "changed_cols"])}
