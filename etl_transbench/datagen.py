"""Seeded, coverage-targeted input data generation (paper Sec. 3.3).

Generators are deterministic under a seed and deliberately include the
discriminating cases that separate correct from plausible-but-wrong
translations: nulls, empty strings, boundary numerics, duplicate keys,
ties in ordering columns, and late/out-of-order records for incremental tasks.
"""
from __future__ import annotations
import string
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class ColumnGen:
    name: str
    dtype: str                      # int | float | string | date | timestamp | category
    null_rate: float = 0.05
    empty_rate: float = 0.0         # strings only: legacy ''/NULL conflation probe
    low: float = 0
    high: float = 1000
    categories: Optional[List[str]] = None
    boundary_values: List = field(default_factory=list)  # injected verbatim


@dataclass
class TableGen:
    name: str
    rows: int
    columns: List[ColumnGen]
    duplicate_key_rate: float = 0.0   # re-emit some rows with same key, new values
    key_columns: List[str] = field(default_factory=list)


def _gen_column(rng: np.random.Generator, cg: ColumnGen, n: int) -> pd.Series:
    if cg.dtype == "int":
        vals = rng.integers(int(cg.low), int(cg.high) + 1, size=n).astype("float")
    elif cg.dtype == "float":
        vals = rng.uniform(cg.low, cg.high, size=n)
    elif cg.dtype == "string":
        letters = np.array(list(string.ascii_uppercase))
        vals = np.array(["".join(rng.choice(letters, size=8)) for _ in range(n)], dtype=object)
    elif cg.dtype == "category":
        vals = rng.choice(np.array(cg.categories, dtype=object), size=n)
    elif cg.dtype in ("date", "timestamp"):
        base = pd.Timestamp("2024-01-01")
        offsets = rng.integers(0, 730, size=n)
        vals = np.array([base + pd.Timedelta(days=int(o)) for o in offsets], dtype=object)
        if cg.dtype == "timestamp":
            secs = rng.integers(0, 86400, size=n)
            vals = np.array([v + pd.Timedelta(seconds=int(s)) for v, s in zip(vals, secs)], dtype=object)
    else:
        raise ValueError(f"unknown dtype {cg.dtype}")

    s = pd.Series(vals, name=cg.name)
    # inject boundary values at deterministic positions
    for i, bv in enumerate(cg.boundary_values):
        if i < n:
            s.iloc[i] = bv
    # nulls / empties
    mask = rng.random(n) < cg.null_rate
    s = s.mask(mask)
    if cg.dtype == "string" and cg.empty_rate > 0:
        emask = rng.random(n) < cg.empty_rate
        s = s.mask(emask & ~mask, "")
    if cg.dtype == "int":
        s = s.astype("Int64")
    return s


def generate_table(tg: TableGen, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({cg.name: _gen_column(rng, cg, tg.rows) for cg in tg.columns})
    if tg.duplicate_key_rate > 0 and tg.key_columns:
        k = max(1, int(tg.rows * tg.duplicate_key_rate))
        dup = df.sample(n=k, random_state=seed).copy()
        for cg in tg.columns:                      # new non-key values, same keys
            if cg.name not in tg.key_columns:
                dup[cg.name] = _gen_column(rng, cg, k).values
        df = pd.concat([df, dup], ignore_index=True)
    return df


def generate_corpus(tables: Dict[str, TableGen], seed: int) -> Dict[str, pd.DataFrame]:
    return {name: generate_table(tg, seed + i) for i, (name, tg) in enumerate(tables.items())}
