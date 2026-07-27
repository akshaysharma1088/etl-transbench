"""Executable legacy oracle for t6c_midnight_split.
Break on gap > 45min OR calendar-date change. session_date is the (single)
date of the session's events — well-defined because sessions cannot span
dates."""
import pandas as pd

def run(inputs):
    e = inputs["events"].sort_values(["user_id", "event_ts", "event_id"]).copy()
    gap = e.groupby("user_id")["event_ts"].diff()
    date_changed = (e["event_ts"].dt.normalize()
                    != e.groupby("user_id")["event_ts"].shift().dt.normalize())
    new_sess = gap.isna() | (gap > pd.Timedelta(minutes=45)) | date_changed
    e["session_num"] = new_sess.groupby(e["user_id"]).cumsum().astype(int)
    e["session_date"] = e["event_ts"].dt.normalize()
    out = (e.groupby(["user_id", "session_num"], as_index=False)
             .agg(session_date=("session_date", "first"),
                  session_start=("event_ts", "min"),
                  session_end=("event_ts", "max"),
                  event_count=("event_id", "size")))
    return {"user_sessions": out}
