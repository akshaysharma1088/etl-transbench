"""Executable legacy oracle for t4c_stale_snapshot.
Step ordering is semantic: DELTA compares the fresh aggregate against the
snapshot AS IT WAS BEFORE Step 3 replaces it. Accounts new to the feed get
delta = avg_score - 0. Accounts only in the old snapshot emit no delta row
and are dropped from the new snapshot (full replace)."""
import pandas as pd

def run(inputs):
    feed = inputs["score_feed"]
    old = inputs["score_snapshot_prior"]
    curr = (feed.groupby("account_id", as_index=False)
                .agg(avg_score=("score", "mean")))
    delta = curr.merge(old.rename(columns={"avg_score": "old_avg"}),
                       on="account_id", how="left")
    delta["score_delta"] = delta["avg_score"] - delta["old_avg"].fillna(0.0)
    return {"delta": delta[["account_id", "score_delta"]],
            "score_snapshot": curr[["account_id", "avg_score"]]}
