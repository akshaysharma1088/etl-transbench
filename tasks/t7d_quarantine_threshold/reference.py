"""Executable legacy oracle for t7d_quarantine_threshold.
Two-level validation: row-level bad flags, then batch-level quarantine when
bad share STRICTLY exceeds 20%. Quarantined batches move whole (good rows
included); others split into clean/rejects."""
import pandas as pd

def run(inputs):
    df = inputs["readings"].copy()
    df["bad"] = df["value"].isna() | (df["value"] < 0) | (df["value"] > 1000)
    stats = df.groupby("batch_id")["bad"].agg(["sum", "size"])
    stats["pct"] = stats["sum"] * 100.0 / stats["size"]
    quarantined = set(stats.index[stats["sum"] * 100 > stats["size"] * 20])
    df["batch_reject_pct"] = df["batch_id"].map((stats["pct"]).round(2))
    q = df[df["batch_id"].isin(quarantined)]
    rest = df[~df["batch_id"].isin(quarantined)]
    cols = ["batch_id", "reading_id", "sensor", "value"]
    return {"readings_clean": rest[~rest["bad"]][cols],
            "readings_rejects": rest[rest["bad"]][cols],
            "readings_quarantine": q[cols + ["batch_reject_pct"]]}
