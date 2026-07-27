"""Executable legacy oracle for t2d_reject_skip_accum.
Invalid rows (qty NULL/<=0, unit_price NULL/<0) are skipped: excluded from
POSTED_TOTALS and from the running total, counted per account. Every account
present in the input emits a reject-count row, including zero counts."""
import pandas as pd

def _invalid(df):
    return (df["qty"].isna() | (df["qty"] <= 0)
            | df["unit_price"].isna() | (df["unit_price"] < 0))

def run(inputs):
    df = inputs["postings"].sort_values(
        ["account_id", "post_date", "post_seq"]).copy()
    bad = _invalid(df)
    good = df[~bad].copy()
    good["post_value"] = good["qty"] * good["unit_price"]
    good["running_total"] = good.groupby("account_id")["post_value"].cumsum()
    rejects = (bad.groupby(df["account_id"]).sum().astype(int)
               .rename("reject_count").reset_index())
    return {
        "posted_totals": good[["account_id", "post_seq", "post_date",
                               "post_value", "running_total"]],
        "reject_counts": rejects,
    }
