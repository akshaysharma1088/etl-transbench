"""Task loading, execution, and scoring harness.

A task directory contains:
    task.json          - metadata: id, category, tier, description, target dialect
    spec.json          - EquivalenceSpec (see equivalence.py)
    reference.py       - run(inputs: dict[str, DataFrame]) -> dict[str, DataFrame]
                         (the executable legacy oracle; may use duckdb internally)
    generator.py       - corpus(seed: int) -> dict[str, DataFrame]
    legacy_artifact.*  - the source artifact shown to the translator
                         (dialect SQL, procedure text, or abstracted dataflow JSON)

Candidates are scored by executing them over k seeded corpora and comparing
against the reference with the equivalence checker. The agent NEVER sees
reference outputs; the harness owns both guardrails from paper Sec. 5.3.
"""
from __future__ import annotations
import importlib.util
import json
import os
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

import pandas as pd

from .equivalence import EquivalenceSpec, compare_outputs

RunFn = Callable[[Dict[str, pd.DataFrame]], Dict[str, pd.DataFrame]]


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@dataclass
class Task:
    task_dir: str
    meta: Dict[str, Any]
    spec: EquivalenceSpec
    reference: RunFn
    corpus: Callable[[int], Dict[str, pd.DataFrame]]
    legacy_artifact: str

    @staticmethod
    def load(task_dir: str) -> "Task":
        with open(os.path.join(task_dir, "task.json")) as f:
            meta = json.load(f)
        spec = EquivalenceSpec.load(os.path.join(task_dir, "spec.json"))
        ref = _load_module(os.path.join(task_dir, "reference.py"), f"ref_{meta['id']}").run
        gen = _load_module(os.path.join(task_dir, "generator.py"), f"gen_{meta['id']}").corpus
        art_name = meta["legacy_artifact"]
        with open(os.path.join(task_dir, art_name)) as f:
            artifact = f.read()
        return Task(task_dir, meta, spec, ref, gen, artifact)


@dataclass
class CostLedger:
    """Per-task cost accounting (paper Sec. 4.3). USD figures are estimates
    computed from per-model price config; tokens are ground truth."""
    entries: List[Dict[str, Any]] = field(default_factory=list)

    def record(self, role: str, model: str, tokens_in: int, tokens_out: int,
               usd: float = 0.0, wall_s: float = 0.0):
        self.entries.append(dict(role=role, model=model, tokens_in=tokens_in,
                                 tokens_out=tokens_out, usd=usd, wall_s=wall_s))

    def totals(self) -> Dict[str, float]:
        t = {"tokens_in": 0, "tokens_out": 0, "usd": 0.0, "wall_s": 0.0}
        for e in self.entries:
            for k in t:
                t[k] += e[k]
        return t


@dataclass
class VerificationResult:
    compiled: bool
    executed: bool
    equivalent: bool
    seeds: List[int]
    reports: List[Dict[str, Any]] = field(default_factory=list)
    error: str = ""


def verify_candidate(task: Task, candidate_run: RunFn,
                     seeds: List[int] = (11, 23, 47)) -> VerificationResult:
    """Differential execution: reference vs candidate over k seeded corpora."""
    reports = []
    for seed in seeds:
        inputs = task.corpus(seed)
        ref_out = task.reference({k: v.copy() for k, v in inputs.items()})
        try:
            cand_out = candidate_run({k: v.copy() for k, v in inputs.items()})
        except Exception:
            return VerificationResult(True, False, False, list(seeds), reports,
                                      error=traceback.format_exc(limit=5))
        rep = compare_outputs(ref_out, cand_out, task.spec)
        reports.append({"seed": seed, **rep})
        if not rep["equivalent"]:
            return VerificationResult(True, True, False, list(seeds), reports)
    return VerificationResult(True, True, True, list(seeds), reports)


def compile_candidate(code: str, entry: str = "run") -> tuple[RunFn | None, str]:
    """Compile candidate source (a module defining run(inputs)->outputs).

    SECURITY NOTE: exec of model-generated code. In the full benchmark this is
    sandboxed (container, no network, resource limits); enforce that before
    running any untrusted model output.
    """
    ns: Dict[str, Any] = {}
    try:
        exec(compile(code, "<candidate>", "exec"), ns)  # noqa: S102 - sandboxed in prod
    except Exception:
        return None, traceback.format_exc(limit=5)
    fn = ns.get(entry)
    if not callable(fn):
        return None, f"candidate does not define callable '{entry}(inputs)'"
    return fn, ""


def discover_tasks(root: str) -> List[str]:
    return sorted(d.path for d in os.scandir(root)
                  if d.is_dir() and os.path.exists(os.path.join(d.path, "task.json")))
