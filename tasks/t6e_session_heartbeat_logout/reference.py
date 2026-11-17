"""Executable legacy oracle for t6e_session_heartbeat_logout.
A running, stateful pass per user: only activity events move the inactivity
clock, a logout closes the session, and a heartbeat with no live session is
dropped."""
import pandas as pd

GAP = pd.Timedelta(minutes=30)


def run(inputs):
    ev = inputs["app_events"].sort_values(["user_id", "event_ts", "event_id"])
    out = []
    for uid, g in ev.groupby("user_id", sort=True):
        cur, num = None, 0
        for e in g.to_dict("records"):
            ts = e["event_ts"]
            if e["event_type"] == "heartbeat":
                if cur is not None and ts - cur["session_end"] <= GAP:
                    cur["event_count"] += 1
                    cur["heartbeat_count"] += 1
                continue
            if cur is None or ts - cur["session_end"] > GAP:
                num += 1
                cur = dict(user_id=uid, session_num=num, session_start=ts, session_end=ts,
                           event_count=0, heartbeat_count=0)
                out.append(cur)
            cur["event_count"] += 1
            cur["session_end"] = ts
            if e["event_type"] == "logout":
                cur = None
    return {"user_sessions": pd.DataFrame(out, columns=["user_id", "session_num", "session_start",
                                                        "session_end", "event_count", "heartbeat_count"])}
