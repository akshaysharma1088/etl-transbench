"""Executable legacy oracle for t5d_asof_reconstruction.
Half-open interval semantics: [eff_start_date, eff_end_date); NULL end = open.
Inner-join: out-of-range and unknown-employee queries produce no row."""
import pandas as pd

def run(inputs):
    h = inputs["dim_emp_hist"]
    q = inputs["asof_queries"]
    m = q.merge(h, on="emp_id", how="inner")
    ok = (m["as_of_date"] >= m["eff_start_date"]) & (
        m["eff_end_date"].isna() | (m["as_of_date"] < m["eff_end_date"]))
    out = m[ok][["query_id", "emp_id", "dept", "grade"]]
    return {"asof_result": out}
