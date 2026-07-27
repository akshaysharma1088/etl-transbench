"""Equivalence specification and checker for ETL-TransBench.

Implements test-based semantic equivalence (paper Sec. 3.2-3.3): after applying
declared normalizations, output relations are compared as multisets (unordered)
or as keyed row matches with per-column tolerances. Produces a structured
report suitable for the LEGATO diagnoser (row-level counterexamples, schema
diffs, per-column mismatch counts).
"""
from __future__ import annotations
import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class ColumnRule:
    """Per-column comparison rule."""
    name: str
    kind: str = "exact"          # exact | float | timestamp | string
    abs_tol: float = 0.0          # for kind=float
    rel_tol: float = 0.0          # for kind=float
    trim: bool = False            # for kind=string
    casefold: bool = False        # for kind=string
    null_equals_empty: bool = False  # legacy '' / NULL conflation
    tz_normalize: Optional[str] = None  # e.g. "UTC" for kind=timestamp


@dataclass
class RelationSpec:
    """Equivalence spec for one output relation."""
    name: str
    key_columns: List[str] = field(default_factory=list)  # [] => pure multiset compare
    ordered: bool = False
    columns: Dict[str, ColumnRule] = field(default_factory=dict)
    ignore_columns: List[str] = field(default_factory=list)  # e.g. load_ts audit cols

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RelationSpec":
        cols = {c["name"]: ColumnRule(**c) for c in d.get("columns", [])}
        return RelationSpec(
            name=d["name"],
            key_columns=d.get("key_columns", []),
            ordered=d.get("ordered", False),
            columns=cols,
            ignore_columns=d.get("ignore_columns", []),
        )


@dataclass
class EquivalenceSpec:
    task_id: str
    relations: List[RelationSpec]

    @staticmethod
    def load(path: str) -> "EquivalenceSpec":
        with open(path) as f:
            d = json.load(f)
        return EquivalenceSpec(
            task_id=d["task_id"],
            relations=[RelationSpec.from_dict(r) for r in d["relations"]],
        )


# --------------------------------------------------------------------------- #
# Normalization
# --------------------------------------------------------------------------- #

def _normalize(df: pd.DataFrame, spec: RelationSpec) -> pd.DataFrame:
    df = df.drop(columns=[c for c in spec.ignore_columns if c in df.columns], errors="ignore").copy()
    for col, rule in spec.columns.items():
        if col not in df.columns:
            continue
        if rule.kind == "string":
            s = df[col].astype("string")
            if rule.null_equals_empty:
                s = s.fillna("")
            if rule.trim:
                s = s.str.strip()
            if rule.casefold:
                s = s.str.casefold()
            df[col] = s
        elif rule.kind == "timestamp":
            s = pd.to_datetime(df[col], errors="coerce", utc=bool(rule.tz_normalize))
            if rule.tz_normalize:
                s = s.dt.tz_convert(rule.tz_normalize)
            df[col] = s
        elif rule.kind == "float":
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
    return df


def _values_equal(a: Any, b: Any, rule: Optional[ColumnRule]) -> bool:
    a_null = pd.isna(a)
    b_null = pd.isna(b)
    if a_null and b_null:
        return True
    if a_null != b_null:
        return False
    if rule and rule.kind == "float":
        return math.isclose(float(a), float(b), rel_tol=rule.rel_tol, abs_tol=rule.abs_tol)
    return a == b


# --------------------------------------------------------------------------- #
# Comparison
# --------------------------------------------------------------------------- #

@dataclass
class RelationReport:
    name: str
    equivalent: bool
    schema_diff: Dict[str, Any] = field(default_factory=dict)
    row_count: Dict[str, int] = field(default_factory=dict)
    mismatched_keys: List[Any] = field(default_factory=list)      # sample, <=10
    column_mismatch_counts: Dict[str, int] = field(default_factory=dict)
    unmatched_reference_rows: int = 0
    unmatched_candidate_rows: int = 0
    detail: str = ""


def compare_relation(reference: pd.DataFrame, candidate: pd.DataFrame,
                     spec: RelationSpec, sample: int = 10) -> RelationReport:
    rep = RelationReport(name=spec.name, equivalent=False)
    ref = _normalize(reference, spec)
    cand = _normalize(candidate, spec)
    rep.row_count = {"reference": len(ref), "candidate": len(cand)}

    ref_cols, cand_cols = set(ref.columns), set(cand.columns)
    if ref_cols != cand_cols:
        rep.schema_diff = {
            "missing_in_candidate": sorted(ref_cols - cand_cols),
            "extra_in_candidate": sorted(cand_cols - ref_cols),
        }
        rep.detail = "schema mismatch"
        return rep
    cols = list(ref.columns)

    if spec.key_columns:
        rep_eq = _compare_keyed(ref, cand, spec, cols, rep, sample)
    elif spec.ordered:
        rep_eq = _compare_ordered(ref, cand, spec, cols, rep, sample)
    else:
        rep_eq = _compare_multiset(ref, cand, spec, cols, rep)
    rep.equivalent = rep_eq
    return rep


def _round_for_hash(df: pd.DataFrame, spec: RelationSpec, cols: List[str]) -> pd.DataFrame:
    """For multiset compare, float-tolerance columns are bucketed by rounding."""
    out = df.copy()
    for c in cols:
        rule = spec.columns.get(c)
        if rule and rule.kind == "float" and (rule.abs_tol or rule.rel_tol):
            tol = rule.abs_tol or 1e-9
            decimals = max(0, -int(math.floor(math.log10(tol))))
            out[c] = out[c].round(decimals)
    return out


def _compare_multiset(ref, cand, spec, cols, rep) -> bool:
    if len(ref) != len(cand):
        rep.detail = "row count mismatch"
        return False
    r = _round_for_hash(ref, spec, cols).sort_values(cols, na_position="last").reset_index(drop=True)
    c = _round_for_hash(cand, spec, cols).sort_values(cols, na_position="last").reset_index(drop=True)
    eq = r.equals(c)
    if not eq:
        neq = (r != c) & ~(r.isna() & c.isna())
        rep.column_mismatch_counts = {k: int(v) for k, v in neq.sum().items() if v > 0}
        rep.detail = "multiset content mismatch"
    return eq


def _compare_ordered(ref, cand, spec, cols, rep, sample) -> bool:
    if len(ref) != len(cand):
        rep.detail = "row count mismatch"
        return False
    ok = True
    for c in cols:
        rule = spec.columns.get(c)
        bad = [i for i in range(len(ref))
               if not _values_equal(ref[c].iloc[i], cand[c].iloc[i], rule)]
        if bad:
            ok = False
            rep.column_mismatch_counts[c] = len(bad)
            rep.mismatched_keys.extend(bad[:sample])
    if not ok:
        rep.detail = "ordered content mismatch"
    return ok


def _compare_keyed(ref, cand, spec, cols, rep, sample) -> bool:
    keys = spec.key_columns
    rk = ref.set_index(keys, drop=False)
    ck = cand.set_index(keys, drop=False)
    if rk.index.has_duplicates or ck.index.has_duplicates:
        # fall back to multiset semantics on duplicate keys
        return _compare_multiset(ref, cand, spec, cols, rep)
    ref_only = rk.index.difference(ck.index)
    cand_only = ck.index.difference(rk.index)
    rep.unmatched_reference_rows = len(ref_only)
    rep.unmatched_candidate_rows = len(cand_only)
    ok = not len(ref_only) and not len(cand_only)
    if not ok:
        rep.mismatched_keys = list(ref_only[:sample]) + list(cand_only[:sample])
        rep.detail = "key set mismatch"
    common = rk.index.intersection(ck.index)
    value_cols = [c for c in cols if c not in keys]
    for c in value_cols:
        rule = spec.columns.get(c)
        bad_keys = [k for k in common
                    if not _values_equal(rk.at[k, c], ck.at[k, c], rule)]
        if bad_keys:
            ok = False
            rep.column_mismatch_counts[c] = len(bad_keys)
            for k in bad_keys[:sample]:
                if k not in rep.mismatched_keys:
                    rep.mismatched_keys.append(k)
            rep.detail = rep.detail or "value mismatch on matched keys"
    return ok


def compare_outputs(reference: Dict[str, pd.DataFrame],
                    candidate: Dict[str, pd.DataFrame],
                    spec: EquivalenceSpec) -> Dict[str, Any]:
    """Compare all output relations of a task. Returns a JSON-able report."""
    reports, all_ok = [], True
    for rs in spec.relations:
        if rs.name not in candidate:
            reports.append(RelationReport(rs.name, False, detail="relation missing in candidate").__dict__)
            all_ok = False
            continue
        r = compare_relation(reference[rs.name], candidate[rs.name], rs)
        reports.append(r.__dict__)
        all_ok = all_ok and r.equivalent
    return {"task_id": spec.task_id, "equivalent": all_ok, "relations": reports}
