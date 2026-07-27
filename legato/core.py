"""LEGATO: Legacy ETL Translation with Agentic Test-grounded Orchestration.

Single-file implementation of the six-role loop (paper Sec. 5):
analyzer -> translator -> [synthesizer is task-owned] -> differential executor
-> diagnoser -> repair, under a cost-governed escalation controller.

The LLM client is pluggable; set ANTHROPIC_API_KEY (or swap the client) to run.
Nothing here ever reads golden outputs, and the repair agent receives only
externally produced evidence (error traces, schema diffs, row counterexamples).
"""
from __future__ import annotations
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from etl_transbench.harness import (Task, CostLedger, VerificationResult,
                                    compile_candidate, verify_candidate)

# --------------------------------------------------------------------------- #
# Pluggable LLM client
# --------------------------------------------------------------------------- #

PRICES_USD_PER_MTOK = {  # update at run time; placeholders for accounting
    "cheap": {"in": 0.25, "out": 1.25},
    "frontier": {"in": 3.00, "out": 15.00},
}


class LLMClient:
    """Anthropic Messages API client; swap `complete` for other providers."""

    def __init__(self, model_cheap: str, model_frontier: str):
        self.models = {"cheap": model_cheap, "frontier": model_frontier}

    def complete(self, tier: str, system: str, user: str,
                 ledger: CostLedger, role: str, max_tokens: int = 4000) -> str:
        import anthropic  # lazy: pip install anthropic
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        t0 = time.time()
        msg = client.messages.create(
            model=self.models[tier], max_tokens=max_tokens,
            system=system, messages=[{"role": "user", "content": user}])
        text = "".join(b.text for b in msg.content if b.type == "text")
        usd = (msg.usage.input_tokens * PRICES_USD_PER_MTOK[tier]["in"]
               + msg.usage.output_tokens * PRICES_USD_PER_MTOK[tier]["out"]) / 1e6
        ledger.record(role, self.models[tier], msg.usage.input_tokens,
                      msg.usage.output_tokens, usd, time.time() - t0)
        return text


# --------------------------------------------------------------------------- #
# Prompts (construct-conditioned; paper Sec. 5.1)
# --------------------------------------------------------------------------- #

TRANSLATOR_SYSTEM = """You translate legacy ETL artifacts into Python.
Output ONLY a Python module inside one ```python code fence. The module must
define run(inputs: dict[str, pandas.DataFrame]) -> dict[str, pandas.DataFrame]
that reproduces the legacy semantics exactly, including null handling, type
coercion, duplicate keys, and tie-breaking. Do not invent columns. Do not
read or write files. Use only pandas and the Python standard library."""

CONSTRUCT_HINTS = {
    "T1": "Dialect SQL: QUALIFY filters on window results AFTER they are computed; replicate Teradata-style null sorting and integer division semantics explicitly.",
    "T2": "Procedural logic: rewrite cursors/loops as set-oriented operations; preserve per-iteration state effects exactly.",
    "T5": "SCD Type 2: close prior current rows (end_date, is_current=0) before inserting new versions; unchanged records must NOT create versions; compare tracked attributes only.",
    "T8": "Incremental/CDC: respect the watermark, apply latest-record-wins per key by event time with deterministic tie-breaks, and make the merge idempotent.",
}

REPAIR_SYSTEM = TRANSLATOR_SYSTEM + """
You will receive your previous code plus EXTERNAL verification evidence
(error traces, schema diffs, mismatched keys, per-column mismatch counts)
from differential execution against the legacy system. Fix the code. Address
the evidence specifically; do not weaken or reinterpret the requirements."""


def extract_code(text: str) -> str:
    m = re.search(r"```python\n(.*?)```", text, re.DOTALL)
    return m.group(1) if m else text


# --------------------------------------------------------------------------- #
# Diagnoser (paper Sec. 5.1): evidence -> classified failure report
# --------------------------------------------------------------------------- #

FAILURE_CLASSES = ["syntactic", "runtime", "schema_mismatch",
                   "semantic_divergence", "relation_missing"]


def diagnose(result: VerificationResult, compile_error: str = "") -> Dict[str, Any]:
    if compile_error:
        return {"class": "syntactic", "evidence": compile_error[-2000:]}
    if not result.executed:
        return {"class": "runtime", "evidence": result.error[-2000:]}
    last = result.reports[-1]
    for rel in last["relations"]:
        if rel["detail"] == "relation missing in candidate":
            return {"class": "relation_missing", "relation": rel["name"], "evidence": rel}
        if rel.get("schema_diff"):
            return {"class": "schema_mismatch", "relation": rel["name"],
                    "evidence": rel["schema_diff"]}
    bad = [r for r in last["relations"] if not r["equivalent"]]
    return {"class": "semantic_divergence",
            "evidence": [{k: r[k] for k in ("name", "detail", "row_count",
                                            "mismatched_keys",
                                            "column_mismatch_counts",
                                            "unmatched_reference_rows",
                                            "unmatched_candidate_rows")}
                         for r in bad]}


# --------------------------------------------------------------------------- #
# Controller: cost-governed escalation (paper Sec. 5.2)
# --------------------------------------------------------------------------- #

@dataclass
class EscalationPolicy:
    """Fixed-threshold policy: start on predicted tier; escalate the repair to
    frontier after `escalate_after` failed cheap repairs; full frontier
    retranslation after `retranslate_after`; halt at budget or max_iters."""
    max_iters: int = 5
    escalate_after: int = 1
    retranslate_after: int = 3
    budget_usd: float = 0.50
    # When False, repair prompts omit the differential evidence and ask the
    # model to critique its own output instead (baseline B3, the ungrounded
    # self-repair setting studied by Olausson et al.).
    grounded: bool = True

    def initial_tier(self, task: Task) -> str:
        hard = {"T2", "T5", "T7", "T8"}
        tier3 = task.meta.get("tier", 1) >= 3
        return "frontier" if (task.meta["category"] in hard or tier3) else "cheap"

    def next_action(self, iters: int, tier: str, spent: float) -> str:
        if spent >= self.budget_usd or iters >= self.max_iters:
            return "halt"
        if iters >= self.retranslate_after:
            return "retranslate_frontier"
        if tier == "cheap" and iters >= self.escalate_after:
            return "repair_frontier"
        return f"repair_{tier}"


@dataclass
class LegatoResult:
    task_id: str
    equivalent: bool
    iterations: int
    final_code: str
    history: List[Dict[str, Any]]
    cost: Dict[str, float]
    handoff: Optional[Dict[str, Any]] = None  # populated on halt


def run_legato(task: Task, llm: LLMClient,
               policy: EscalationPolicy = EscalationPolicy()) -> LegatoResult:
    ledger = CostLedger()
    history: List[Dict[str, Any]] = []
    hint = CONSTRUCT_HINTS.get(task.meta["category"], "")
    base_user = (f"Task category: {task.meta['category']} ({task.meta['description']})\n"
                 f"Construct guidance: {hint}\n\nLEGACY ARTIFACT:\n{task.legacy_artifact}\n\n"
                 f"Input relations and dtypes are exactly those of the artifact. "
                 f"Produce output relations named: "
                 f"{[r.name for r in task.spec.relations]}.")

    tier = policy.initial_tier(task)
    code = extract_code(llm.complete(tier, TRANSLATOR_SYSTEM, base_user, ledger, "translator"))

    for it in range(policy.max_iters + 1):
        fn, cerr = compile_candidate(code)
        result = (verify_candidate(task, fn) if fn else
                  VerificationResult(False, False, False, [], []))
        report = diagnose(result, cerr)
        history.append({"iter": it, "tier": tier, "class": report["class"]
                        if not result.equivalent else "equivalent"})
        if result.equivalent:
            return LegatoResult(task.meta["id"], True, it, code, history, ledger.totals())

        action = policy.next_action(it + 1, tier, ledger.totals()["usd"])
        if action == "halt":
            handoff = {"failure_report": report, "best_candidate": code,
                       "history": history}
            return LegatoResult(task.meta["id"], False, it, code, history,
                                ledger.totals(), handoff)
        if action == "retranslate_frontier":
            tier = "frontier"
            code = extract_code(llm.complete(tier, TRANSLATOR_SYSTEM, base_user,
                                             ledger, "translator"))
            continue
        if action == "repair_frontier":
            tier = "frontier"
        if policy.grounded:
            repair_user = (base_user + "\n\nPREVIOUS CODE:\n```python\n" + code +
                           "\n```\n\nVERIFICATION EVIDENCE (external, ground truth):\n" +
                           json.dumps(report, default=str, indent=2)[:6000])
        else:
            # B3: the model is told only THAT it failed, never how. No row-level
            # counterexamples, no schema diff, no error trace.
            repair_user = (base_user + "\n\nPREVIOUS CODE:\n```python\n" + code +
                           "\n```\n\nThis translation was judged NOT equivalent to the "
                           "legacy program. No further diagnostic information is "
                           "available. Review your own code, identify the most likely "
                           "semantic divergence from the legacy artifact, and emit a "
                           "corrected full program.")
        code = extract_code(llm.complete(tier, REPAIR_SYSTEM, repair_user,
                                         ledger, "repair"))

    return LegatoResult(task.meta["id"], False, policy.max_iters, code, history,
                        ledger.totals())
