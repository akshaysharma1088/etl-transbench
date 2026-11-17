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
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from etl_transbench.harness import (Task, CostLedger, VerificationResult,
                                    compile_candidate, verify_candidate)

# --------------------------------------------------------------------------- #
# Pluggable LLM client
# --------------------------------------------------------------------------- #

# USD per million tokens, by tier. These are list prices at the time of the
# run and can be replaced with --prices; token counts are stored per call, so
# any cost figure can be recomputed from the raw results.
# Output cap per call. It has to leave room for the model's reasoning as well
# as the program: the July run used 4,000 and the frontier model sometimes
# spent all of it before writing any code.
MAX_TOKENS = 16000

PRICES_USD_PER_MTOK = {
    "cheap": {"in": 1.00, "out": 5.00},
    "frontier": {"in": 3.00, "out": 15.00},
}


class LLMClient:
    """Anthropic Messages API client; swap `complete` for other providers."""

    def __init__(self, model_cheap: str, model_frontier: str,
                 temperature: Optional[float] = None, prices: Optional[dict] = None):
        self.models = {"cheap": model_cheap, "frontier": model_frontier}
        self.temperature = temperature
        self.prices = prices or PRICES_USD_PER_MTOK
        self.resolved: Dict[str, str] = {}  # tier -> model id the API reports
        self.truncated: Dict[str, int] = {}  # tier -> replies cut off at max_tokens
        self.retried = 0                     # replies re-requested after a dropped connection
        self._lock = threading.Lock()
        self._client = None

    def _stream_once(self, tier, cap, system, user, extra, tries: int = 6):
        """One streamed reply. A connection that drops part-way through a
        stream is not retried by the SDK, so it is retried here; the partial
        reply is discarded and was not billed as a completed message."""
        import anthropic
        transient = (anthropic.APIConnectionError, anthropic.APITimeoutError,
                     anthropic.InternalServerError, anthropic.RateLimitError)

        def is_transient(exc) -> bool:
            # The HTTP layer under the SDK has changed package name between SDK
            # versions, so its errors are recognised by module, not by import.
            mod = type(exc).__module__.split(".")[0]
            return isinstance(exc, transient) or mod.startswith(("httpx", "httpcore", "h11"))

        for i in range(tries):
            try:
                with self._client.messages.stream(  # no temperature given: the API default, 1.0
                        model=self.models[tier], max_tokens=cap, system=system,
                        messages=[{"role": "user", "content": user}], **extra) as stream:
                    return stream.get_final_message()
            except Exception as exc:
                if not is_transient(exc) or i == tries - 1:
                    raise
                with self._lock:
                    self.retried += 1
                print(f"  connection problem ({type(exc).__name__}), retrying in {5 * 2 ** i}s", flush=True)
                time.sleep(5 * 2 ** i)

    def complete(self, tier: str, system: str, user: str,
                 ledger: CostLedger, role: str, max_tokens: int = MAX_TOKENS) -> str:
        if self._client is None:
            import anthropic  # lazy: pip install anthropic
            self._client = anthropic.Anthropic(max_retries=6)  # reads ANTHROPIC_API_KEY
        extra = {} if self.temperature is None else {"temperature": self.temperature}
        text = ""
        # max_tokens caps everything the model emits, its reasoning included.
        # A reply cut off at the cap can have no code in it at all, which would
        # be scored as a failed translation. So a cut-off reply is asked for
        # once more with twice the room, and every cut-off is counted.
        for attempt, cap in enumerate((max_tokens, 2 * max_tokens)):
            t0 = time.time()
            msg = self._stream_once(tier, cap, system, user, extra)
            self.resolved[tier] = getattr(msg, "model", self.models[tier])
            text = "".join(b.text for b in msg.content if b.type == "text")
            usd = (msg.usage.input_tokens * self.prices[tier]["in"]
                   + msg.usage.output_tokens * self.prices[tier]["out"]) / 1e6
            ledger.record(role, self.models[tier], msg.usage.input_tokens,
                          msg.usage.output_tokens, usd, time.time() - t0)
            ledger.entries[-1]["stop_reason"] = msg.stop_reason
            if msg.stop_reason != "max_tokens":
                break
            with self._lock:
                self.truncated[tier] = self.truncated.get(tier, 0) + 1
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


def trace_only(report: Dict[str, Any]) -> Dict[str, Any]:
    """The report with row-level detail removed (ablation).

    Error traces, schema diffs and a missing relation are kept, since a
    compiler or runtime would give those anyway. For a silent value divergence
    only the names of the relations that differ remain: no keys, no counts.
    """
    if report["class"] != "semantic_divergence":
        return report
    return {"class": "semantic_divergence",
            "evidence": [{"name": r["name"], "detail": "outputs differ"}
                         for r in report["evidence"]]}


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
    # What a grounded repair prompt carries: "full" (the whole report) or
    # "trace_only" (see trace_only above). Ignored when grounded is False.
    evidence: str = "full"
    # Construct-conditioned guidance in the prompts (ablation: False).
    use_hints: bool = True
    # Force every call onto one tier, "cheap" or "frontier" (ablation of the
    # escalation policy). None keeps the difficulty estimate and escalation.
    fixed_tier: Optional[str] = None

    def initial_tier(self, task: Task) -> str:
        if self.fixed_tier:
            return self.fixed_tier
        hard = {"T2", "T5", "T7", "T8"}
        tier3 = task.meta.get("tier", 1) >= 3
        return "frontier" if (task.meta["category"] in hard or tier3) else "cheap"

    def next_action(self, iters: int, tier: str, spent: float) -> str:
        if spent >= self.budget_usd or iters >= self.max_iters:
            return "halt"
        if self.fixed_tier:
            return f"repair_{tier}"
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
    # Equivalence of the final candidate on corpora the loop never saw. None
    # when no held-out seeds were given.
    heldout_equivalent: Optional[bool] = None


def input_interface(task: Task) -> str:
    """The keys and columns of `inputs`, as the program will receive them.

    Names and types only, taken from a generated corpus; no rows. A legacy
    artifact usually writes table names in upper case, and without this the
    translator has to guess the dictionary keys it reads from.
    """
    lines = []
    for name, df in task.corpus(11).items():
        cols = ", ".join(f"{c} ({df[c].dtype})" for c in df.columns)
        lines.append(f'  inputs["{name}"]: {cols}')
    return "\n".join(lines)


def base_prompt(task: Task, use_hints: bool = True) -> str:
    hint = CONSTRUCT_HINTS.get(task.meta["category"], "") if use_hints else ""
    return (f"Task category: {task.meta['category']} ({task.meta['description']})\n"
            f"Construct guidance: {hint}\n\nLEGACY ARTIFACT:\n{task.legacy_artifact}\n\n"
            f"`inputs` is a dict of pandas DataFrames with exactly these keys "
            f"(case-sensitive) and columns:\n{input_interface(task)}\n\n"
            f"Return a dict of DataFrames with output relations named: "
            f"{[r.name for r in task.spec.relations]}.")


def initial_translation(task: Task, llm: LLMClient, policy: "EscalationPolicy",
                        ledger: CostLedger) -> str:
    """The first candidate. Depends only on the tier and the hint setting, so
    one call can be shared by every configuration that has the same two."""
    return extract_code(llm.complete(policy.initial_tier(task), TRANSLATOR_SYSTEM,
                                     base_prompt(task, policy.use_hints),
                                     ledger, "translator"))


def run_legato(task: Task, llm: LLMClient,
               policy: EscalationPolicy = EscalationPolicy(),
               initial_code: Optional[str] = None,
               dev_seeds: Optional[List[int]] = None,
               heldout_seeds: Optional[List[int]] = None) -> LegatoResult:
    """Translate, verify and repair one task.

    initial_code: a first candidate made earlier (see initial_translation), so
        several configurations can start from the same one. Its cost is then
        accounted for by the caller.
    dev_seeds: corpora the loop verifies against and draws repair evidence from.
    heldout_seeds: corpora used only to score the final candidate. Nothing
        from them ever reaches a prompt.
    """
    ledger = CostLedger()
    history: List[Dict[str, Any]] = []
    base_user = base_prompt(task, policy.use_hints)
    verify_kw = {"seeds": tuple(dev_seeds)} if dev_seeds else {}

    def heldout(fn) -> Optional[bool]:
        if not heldout_seeds:
            return None
        return bool(fn) and verify_candidate(task, fn, seeds=tuple(heldout_seeds)).equivalent

    tier = policy.initial_tier(task)
    code = (initial_code if initial_code is not None
            else initial_translation(task, llm, policy, ledger))

    for it in range(policy.max_iters + 1):
        fn, cerr = compile_candidate(code)
        result = (verify_candidate(task, fn, **verify_kw) if fn else
                  VerificationResult(False, False, False, [], []))
        report = diagnose(result, cerr)
        history.append({"iter": it, "tier": tier, "class": report["class"]
                        if not result.equivalent else "equivalent"})
        if result.equivalent:
            return LegatoResult(task.meta["id"], True, it, code, history, ledger.totals(),
                                heldout_equivalent=heldout(fn))

        action = policy.next_action(it + 1, tier, ledger.totals()["usd"])
        if action == "halt":
            handoff = {"failure_report": report, "best_candidate": code,
                       "history": history}
            return LegatoResult(task.meta["id"], False, it, code, history,
                                ledger.totals(), handoff,
                                heldout_equivalent=heldout(fn))
        if action == "retranslate_frontier":
            tier = "frontier"
            code = extract_code(llm.complete(tier, TRANSLATOR_SYSTEM, base_user,
                                             ledger, "translator"))
            continue
        if action == "repair_frontier":
            tier = "frontier"
        if policy.grounded:
            shown = trace_only(report) if policy.evidence == "trace_only" else report
            repair_user = (base_user + "\n\nPREVIOUS CODE:\n```python\n" + code +
                           "\n```\n\nVERIFICATION EVIDENCE (external, ground truth):\n" +
                           json.dumps(shown, default=str, indent=2)[:6000])
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

    fn, _ = compile_candidate(code)
    return LegatoResult(task.meta["id"], False, policy.max_iters, code, history,
                        ledger.totals(), heldout_equivalent=heldout(fn))
