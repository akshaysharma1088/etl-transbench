"""Contamination-control perturbation harness (paper Sec. 4.1).

Re-synthesizes a task's surface — relation names, column names, and string
literals in the legacy artifact — under a seeded mapping, so a model cannot
succeed by recalling a memorized solution. The reference oracle still runs on
canonical names; the wrapper renames perturbed inputs back to canonical before
invoking it and renames reference outputs forward, so verification compares in
the PERTURBED space the candidate actually sees.

Usage:
    pt = perturb_task(Task.load(dir), seed=7)
    pt.legacy_artifact          # perturbed text shown to the translator
    verify_candidate(pt, fn)    # candidate must use perturbed names
"""
from __future__ import annotations
import copy
import re
from dataclasses import replace
from typing import Dict

import pandas as pd

from .harness import Task

_SYLLABLES = ["zor", "vex", "qua", "mip", "tal", "rud", "fen", "lox",
              "gab", "nim", "pyx", "sev", "wug", "kez", "dro", "yat"]


def _fresh_name(rng, used: set) -> str:
    while True:
        n = "".join(rng.choice(len(_SYLLABLES)) and _SYLLABLES[rng.integers(0, len(_SYLLABLES))]
                    or _SYLLABLES[rng.integers(0, len(_SYLLABLES))] for _ in range(3))
        n = "_".join(_SYLLABLES[rng.integers(0, len(_SYLLABLES))] for _ in range(2)) \
            + str(rng.integers(10, 99))
        if n not in used:
            used.add(n)
            return n


def build_mapping(task: Task, seed: int) -> Dict[str, str]:
    """Map every input/output relation name and column name to a fresh token."""
    import numpy as np
    rng = np.random.default_rng(seed)
    used: set = set()
    mapping: Dict[str, str] = {}
    sample = task.corpus(0)
    for rel, df in sample.items():
        mapping.setdefault(rel, _fresh_name(rng, used))
        for col in df.columns:
            mapping.setdefault(col, _fresh_name(rng, used))
    ref_out = task.reference({k: v.copy() for k, v in sample.items()})
    for rel, df in ref_out.items():
        mapping.setdefault(rel, _fresh_name(rng, used))
        for col in df.columns:
            mapping.setdefault(col, _fresh_name(rng, used))
    return mapping


def _apply_text(text: str, mapping: Dict[str, str]) -> str:
    # longest-first word-boundary replacement, case-insensitive (SQL artifacts
    # often use upper case for the same identifiers)
    for k in sorted(mapping, key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(k)}\b", mapping[k], text, flags=re.IGNORECASE)
    return text


def _rename_df(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    return df.rename(columns={c: mapping.get(c, c) for c in df.columns})


def perturb_task(task: Task, seed: int) -> Task:
    mapping = build_mapping(task, seed)
    inverse = {v: k for k, v in mapping.items()}

    def perturbed_corpus(s: int):
        return {mapping.get(k, k): _rename_df(v, mapping)
                for k, v in task.corpus(s).items()}

    def perturbed_reference(inputs):
        canonical = {inverse.get(k, k): _rename_df(v, inverse)
                     for k, v in inputs.items()}
        out = task.reference(canonical)
        return {mapping.get(k, k): _rename_df(v, mapping) for k, v in out.items()}

    spec = copy.deepcopy(task.spec)
    for rs in spec.relations:
        rs.name = mapping.get(rs.name, rs.name)
        rs.key_columns = [mapping.get(c, c) for c in rs.key_columns]
        rs.ignore_columns = [mapping.get(c, c) for c in rs.ignore_columns]
        rs.columns = {mapping.get(c, c): replace(rule, name=mapping.get(c, c))
                      for c, rule in rs.columns.items()}

    return Task(task_dir=task.task_dir,
                meta={**task.meta, "perturbation_seed": seed},
                spec=spec,
                reference=perturbed_reference,
                corpus=perturbed_corpus,
                legacy_artifact=_apply_text(task.legacy_artifact, mapping))
