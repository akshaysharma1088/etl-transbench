"""Executable legacy oracle for t6f_cross_device_session_merge."""
import pandas as pd

GAP = pd.Timedelta(minutes=5)


def run(inputs):
    out = []
    ds = inputs["device_sessions"].sort_values(["user_id", "start_ts", "end_ts", "session_id"])
    for uid, g in ds.groupby("user_id", sort=True):
        cur, num = None, 0
        for s in g.to_dict("records"):
            if cur is not None and s["start_ts"] <= cur["end_ts"] + GAP:
                cur["end_ts"] = max(cur["end_ts"], s["end_ts"])
                cur["_devices"].add(s["device_id"])
                cur["source_count"] += 1
                continue
            num += 1
            cur = dict(user_id=uid, merged_num=num, start_ts=s["start_ts"], end_ts=s["end_ts"],
                       _devices={s["device_id"]}, source_count=1)
            out.append(cur)
    for r in out:
        r["device_count"] = len(r.pop("_devices"))
    return {"merged_sessions": pd.DataFrame(out, columns=["user_id", "merged_num", "start_ts", "end_ts",
                                                          "device_count", "source_count"])}
