"""Executable legacy oracle for t1d_tsql_top_ties.
TOP (5) WITH TIES == keep every row whose RANK() by score DESC <= 5.
'+' concat propagates NULL: if either side is NULL the label is NULL."""
import pandas as pd

def run(inputs):
    df = inputs["branch_scores"]
    df = df[df["active"] == 1].copy()
    df["manager_norm"] = df["manager"].fillna("UNASSIGNED")
    def _label(row):
        if pd.isna(row["branch_code"]) or pd.isna(row["region_code"]):
            return None
        return f'{row["branch_code"]}-{row["region_code"]}'
    df["branch_label"] = df.apply(_label, axis=1)
    df["rk"] = df["score"].rank(method="min", ascending=False)
    out = df[df["rk"] <= 5][["branch_id", "manager_norm", "branch_label", "score"]]
    return {"top_branches": out}
