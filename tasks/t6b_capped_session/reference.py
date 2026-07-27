"""Executable legacy oracle for t6b_capped_session.
Session breaks on gap > 20min OR when the event lands more than 4h after the
current session's start (stateful cap: comparisons reference the session
start, which advances at each break). Exactly-at-boundary events stay."""
import pandas as pd

def run(inputs):
    e = inputs["events"].sort_values(["user_id", "event_ts", "event_id"]).copy()
    gap_lim = pd.Timedelta(minutes=20)
    cap = pd.Timedelta(hours=4)
    sess_nums = []
    prev_user = None
    for row in e.itertuples(index=False):
        if row.user_id != prev_user:
            n = 1
            start = row.event_ts
            prev_ts = row.event_ts
            prev_user = row.user_id
        else:
            if (row.event_ts - prev_ts > gap_lim) or (row.event_ts - start > cap):
                n += 1
                start = row.event_ts
            prev_ts = row.event_ts
        sess_nums.append(n)
    e["session_num"] = sess_nums
    out = (e.groupby(["user_id", "session_num"], as_index=False)
             .agg(session_start=("event_ts", "min"),
                  session_end=("event_ts", "max"),
                  event_count=("event_id", "size")))
    return {"user_sessions": out}
