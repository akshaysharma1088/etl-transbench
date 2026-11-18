"""Counterexamples for repair prompts.

A summary such as "12 rows differ in column amount" says that a translation is
wrong but not how. A counterexample shows it: for a few failing keys, the
input rows that involve that key, the rows the legacy system produced, and the
rows the candidate produced.

Everything here is drawn from DEVELOPMENT corpora. The score is computed on
held-out corpora that never reach a prompt, so a candidate that only patches
the examples it was shown does not score.
"""
from __future__ import annotations
import json
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from etl_transbench.harness import Task

MAX_KEYS = 3          # failing keys shown per output relation
MAX_ROWS = 12         # rows shown per table, per key


def _records(df: pd.DataFrame, limit: int = MAX_ROWS) -> List[dict]:
    return json.loads(df.head(limit).to_json(orient="records", date_format="iso"))


def _key_frame(df: pd.DataFrame, keys: List[str]) -> pd.DataFrame:
    """The key columns as strings, so keys compare the same way whatever type
    each side stored them in."""
    out = pd.DataFrame(index=df.index)
    for k in keys:
        col = df[k]
        if pd.api.types.is_datetime64_any_dtype(col):
            out[k] = col.dt.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            num = pd.to_numeric(col, errors="coerce")
            whole = num.notna() & (num == num.round())
            out[k] = col.astype(str)
            out.loc[whole, k] = num[whole].astype("int64").astype(str)
    return out


def _failing_keys(ref: pd.DataFrame, cand: pd.DataFrame, keys: List[str],
                  cols: List[str]) -> List[tuple]:
    """Up to MAX_KEYS keys whose rows differ: wrong values first, then rows the
    candidate is missing, then rows it should not have produced."""
    rk = _key_frame(ref, keys).apply(tuple, axis=1)
    ck = _key_frame(cand, keys).apply(tuple, axis=1)
    rset, cset = set(rk), set(ck)
    wrong = []
    shared = [c for c in cols if c in ref.columns and c in cand.columns and c not in keys]
    r_first = {k: row for k, row in zip(rk, ref[shared].itertuples(index=False, name=None))}
    c_first = {k: row for k, row in zip(ck, cand[shared].itertuples(index=False, name=None))}
    for k in sorted(rset & cset):
        if any(not (pd.isna(x) and pd.isna(y)) and str(x) != str(y) and not _close(x, y)
               for x, y in zip(r_first[k], c_first[k])):
            wrong.append(k)
            if len(wrong) >= MAX_KEYS:
                break
    missing = sorted(rset - cset)[:MAX_KEYS]
    extra = sorted(cset - rset)[:MAX_KEYS]
    picked: List[tuple] = []
    for group in (wrong, missing, extra):
        for k in group:
            if k not in picked and len(picked) < MAX_KEYS:
                picked.append(k)
    return picked


def _close(x, y) -> bool:
    try:
        return abs(float(x) - float(y)) <= 1e-6
    except (TypeError, ValueError):
        return False


def _rows_for(df: pd.DataFrame, keys: List[str], key: tuple) -> pd.DataFrame:
    if not len(df):
        return df
    mask = [k == key for k in _key_frame(df, keys).apply(tuple, axis=1)]
    return df[mask]


def _input_rows(inputs: Dict[str, pd.DataFrame], keys: List[str], key: tuple) -> Dict[str, List[dict]]:
    """Input rows that concern the failing key.

    First, the rows of every input table whose first matching key column has
    the key's value. Then one hop further: an identifier (a column named
    `*_id`) found in those rows pulls the rows with the same identifier from
    the other input tables, so a failing fact row brings its dimension rows.
    """
    out: Dict[str, List[dict]] = {}
    ids: Dict[str, set] = {}
    for name, df in inputs.items():
        col = next((k for k in keys if k in df.columns), None)
        if col is None:
            continue
        hit = df[_key_frame(df, [col])[col] == key[keys.index(col)]]
        if len(hit):
            out[name] = _records(hit)
            for c in hit.columns:
                if c.endswith("_id"):
                    ids.setdefault(c, set()).update(_key_frame(hit, [c])[c].head(MAX_ROWS))
    for name, df in inputs.items():
        if name in out:
            continue
        for c, values in ids.items():
            if c in df.columns:
                hit = df[_key_frame(df, [c])[c].isin(values)]
                if len(hit):
                    out[name] = _records(hit)
                break
    return out


def build(task: Task, candidate_run: Callable, seed: int) -> Optional[Dict[str, Any]]:
    """A counterexample from one development corpus, or None when nothing
    useful can be shown (the candidate crashes, or the outputs have no keys)."""
    try:
        inputs = task.corpus(seed)
        fresh = lambda d: {k: v.copy() for k, v in d.items()}
        ref_out = task.reference(fresh(inputs))
        cand_out = candidate_run(fresh(inputs))
        note = None
        feed = task.meta.get("replay")
        if feed and _same(task, ref_out, cand_out):
            # The first pass agrees, so the failure is on the replay pass: the
            # job's own output fed back as the prior state, same events.
            second_ref, second_cand = fresh(inputs), fresh(inputs)
            for out_rel, in_rel in feed.items():
                second_ref[in_rel] = ref_out[out_rel][list(inputs[in_rel].columns)].copy()
                second_cand[in_rel] = cand_out[out_rel][list(inputs[in_rel].columns)].copy()
            ref_out, cand_out, inputs = task.reference(fresh(second_ref)), candidate_run(fresh(second_cand)), second_cand
            note = ("The first run is correct. These rows are from a SECOND run, where the job's own "
                    "output was fed back as the prior state with the same events. A correct job "
                    "reproduces its first output.")
        relations = []
        for rs in task.spec.relations:
            if rs.name not in ref_out or rs.name not in cand_out or not rs.key_columns:
                continue
            ref, cand = ref_out[rs.name], cand_out[rs.name]
            if any(k not in ref.columns or k not in cand.columns for k in rs.key_columns):
                continue
            cols = [c for c in ref.columns if c not in rs.ignore_columns]
            cases = []
            for key in _failing_keys(ref, cand, rs.key_columns, cols):
                cases.append({
                    "key": dict(zip(rs.key_columns, key)),
                    "input_rows": _input_rows(inputs, rs.key_columns, key),
                    "legacy_system_produced": _records(_rows_for(ref, rs.key_columns, key)),
                    "your_code_produced": _records(_rows_for(cand, rs.key_columns, key)),
                })
            if cases:
                relations.append({"relation": rs.name, "cases": cases})
        if not relations:
            return None
        out = {"corpus_seed": seed, "relations": relations}
        if note:
            out["note"] = note
        return out
    except Exception:
        return None


def _same(task: Task, a, b) -> bool:
    from etl_transbench.equivalence import compare_outputs
    try:
        return bool(compare_outputs(a, b, task.spec)["equivalent"])
    except Exception:
        return False
