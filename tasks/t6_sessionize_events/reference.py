import pandas as pd

def run(inputs):
    e = inputs["events"].sort_values(["user_id", "event_ts", "event_id"]).copy()
    gap = e.groupby("user_id")["event_ts"].diff()
    new_sess = gap.isna() | (gap > pd.Timedelta(minutes=30))   # STRICT >
    e["session_num"] = new_sess.groupby(e["user_id"]).cumsum().astype(int)
    out = (e.groupby(["user_id", "session_num"], as_index=False)
             .agg(session_start=("event_ts", "min"),
                  session_end=("event_ts", "max"),
                  event_count=("event_id", "size")))
    return {"user_sessions": out}
