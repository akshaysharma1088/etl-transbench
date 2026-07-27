"""Executable legacy oracle for t3c_router_first_match.
Router rules are ordered, first match wins, each row lands on exactly one
port. Rules OVERLAP by design: a 12000-amount claim matches both high_value
and manual_review, and must land on high_value (earlier rule). The standard
(default) port is not an output of this graph."""
import numpy as np
import pandas as pd

def run(inputs):
    df = inputs["claims"].copy()
    r1 = (df["amount"] <= 500) & (df["photos_attached"] == 1)
    r2 = (df["amount"] > 10000)
    r3 = (df["photos_attached"] == 0) | (df["amount"] > 500)
    port = np.select([r1, r2, r3],
                     ["fast_track", "high_value", "manual_review"],
                     default="standard")
    cols = ["claim_id", "amount", "photos_attached"]
    return {
        "claims_fast_track": df.loc[port == "fast_track", cols],
        "claims_high_value": df.loc[port == "high_value", cols],
        "claims_manual_review": df.loc[port == "manual_review", cols],
    }
