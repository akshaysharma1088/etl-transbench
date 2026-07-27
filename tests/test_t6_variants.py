"""Verification for new T6 tasks: oracle self-check + planted classic-migration bugs."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from etl_transbench.harness import Task, verify_candidate, compile_candidate

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

def check(tid, code, expect_eq, label):
    task = Task.load(os.path.join(ROOT, "tasks", tid))
    fn, err = compile_candidate(code)
    assert fn, f"{label}: compile failed: {err}"
    res = verify_candidate(task, fn)
    assert res.equivalent == expect_eq, (
        f"{label}: expected equivalent={expect_eq}, got {res.equivalent}; "
        f"report={res.reports[-1] if res.reports else res.error}")
    print(f"PASS  {label}")

for tid in ["t6b_capped_session", "t6c_midnight_split", "t6d_channel_interleave"]:
    task = Task.load(os.path.join(ROOT, "tasks", tid))
    res = verify_candidate(task, task.reference)
    assert res.equivalent, f"{tid}: oracle self-verification FAILED: {res.reports or res.error}"
    print(f"PASS  {tid}: oracle self-verifies")

# t6b bug: gap-only sessionization (ignores the 4h cap)
bug_b1 = '''
import pandas as pd
def run(inputs):
    e = inputs["events"].sort_values(["user_id", "event_ts", "event_id"]).copy()
    gap = e.groupby("user_id")["event_ts"].diff()
    new_sess = gap.isna() | (gap > pd.Timedelta(minutes=20))       # WRONG: no cap
    e["session_num"] = new_sess.groupby(e["user_id"]).cumsum().astype(int)
    out = (e.groupby(["user_id", "session_num"], as_index=False)
             .agg(session_start=("event_ts", "min"), session_end=("event_ts", "max"),
                  event_count=("event_id", "size")))
    return {"user_sessions": out}
'''
check("t6b_capped_session", bug_b1, False, "t6b: gap-only (cap ignored) -> caught")

# t6b bug 2: cap measured against FIRST event of user (fixed anchor, not per-session)
bug_b2 = '''
import pandas as pd
def run(inputs):
    e = inputs["events"].sort_values(["user_id", "event_ts", "event_id"]).copy()
    gap_lim = pd.Timedelta(minutes=20); cap = pd.Timedelta(hours=4)
    sess = []
    prev_user = None
    for row in e.itertuples(index=False):
        if row.user_id != prev_user:
            n = 1; anchor = row.event_ts; prev_ts = row.event_ts; prev_user = row.user_id
        else:
            if (row.event_ts - prev_ts > gap_lim) or (row.event_ts - anchor > cap):
                n += 1
                # WRONG: anchor only advances on cap-driven 4h grid from user start
                while row.event_ts - anchor > cap:
                    anchor = anchor + cap
            prev_ts = row.event_ts
        sess.append(n)
    e["session_num"] = sess
    out = (e.groupby(["user_id", "session_num"], as_index=False)
             .agg(session_start=("event_ts", "min"), session_end=("event_ts", "max"),
                  event_count=("event_id", "size")))
    return {"user_sessions": out}
'''
check("t6b_capped_session", bug_b2, False, "t6b: fixed 4h grid vs session-start anchor -> caught")

# t6c bug: gap-only (sessions cross midnight)
bug_c = '''
import pandas as pd
def run(inputs):
    e = inputs["events"].sort_values(["user_id", "event_ts", "event_id"]).copy()
    gap = e.groupby("user_id")["event_ts"].diff()
    new_sess = gap.isna() | (gap > pd.Timedelta(minutes=45))       # WRONG: no midnight split
    e["session_num"] = new_sess.groupby(e["user_id"]).cumsum().astype(int)
    e["session_date"] = e["event_ts"].dt.normalize()
    out = (e.groupby(["user_id", "session_num"], as_index=False)
             .agg(session_date=("session_date", "first"),
                  session_start=("event_ts", "min"), session_end=("event_ts", "max"),
                  event_count=("event_id", "size")))
    return {"user_sessions": out}
'''
check("t6c_midnight_split", bug_c, False, "t6c: sessions cross midnight -> caught")

# t6d bug: user-level sessionization then channel carried along
bug_d = '''
import pandas as pd
def run(inputs):
    e = inputs["events"].sort_values(["user_id", "event_ts", "event_id"]).copy()
    gap = e.groupby("user_id")["event_ts"].diff()                  # WRONG: per-user gaps
    new_sess = gap.isna() | (gap > pd.Timedelta(minutes=25))
    e["session_num"] = new_sess.groupby(e["user_id"]).cumsum().astype(int)
    out = (e.groupby(["user_id", "channel", "session_num"], as_index=False)
             .agg(session_start=("event_ts", "min"), session_end=("event_ts", "max"),
                  event_count=("event_id", "size")))
    return {"channel_sessions": out}
'''
check("t6d_channel_interleave", bug_d, False, "t6d: user-level gaps bridge channel sessions -> caught")

print("\nALL NEW T6 TASKS VERIFIED (3 oracles, 4 bug probes)")
