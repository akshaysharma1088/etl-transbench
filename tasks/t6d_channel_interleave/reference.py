"""Executable legacy oracle for t6d_channel_interleave.
Independent sessionization per (user_id, channel): gaps measured within the
channel stream only."""
import pandas as pd

def run(inputs):
    e = inputs["events"].sort_values(
        ["user_id", "channel", "event_ts", "event_id"]).copy()
    gap = e.groupby(["user_id", "channel"])["event_ts"].diff()
    new_sess = gap.isna() | (gap > pd.Timedelta(minutes=25))
    e["session_num"] = (new_sess.groupby([e["user_id"], e["channel"]])
                        .cumsum().astype(int))
    out = (e.groupby(["user_id", "channel", "session_num"], as_index=False)
             .agg(session_start=("event_ts", "min"),
                  session_end=("event_ts", "max"),
                  event_count=("event_id", "size")))
    return {"channel_sessions": out}
