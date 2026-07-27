"""Executable legacy oracle for t2c_locf_carry_forward.
LOCF strictly within account (ordered by obs_date, obs_seq). Leading NULLs in
an account remain NULL with was_carried = 0; filled NULLs get was_carried = 1."""
import pandas as pd

def run(inputs):
    df = inputs["rate_feed"].sort_values(
        ["account_id", "obs_date", "obs_seq"]).copy()
    filled = df.groupby("account_id", group_keys=False)["rate"].ffill()
    df["was_carried"] = (df["rate"].isna() & filled.notna()).astype(int)
    df["rate_filled"] = filled
    return {"rate_filled": df[["account_id", "obs_seq", "obs_date",
                               "rate_filled", "was_carried"]]}
