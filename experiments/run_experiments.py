"""Experiment runner for the Section 6 protocol.

TWO MODES, deliberately impossible to confuse:

  --mock   Harness validation. A scripted stand-in "model" returns canned
           candidates (a known-buggy variant first, the corrected version on
           repair). This exercises every stage of the pipeline — translation,
           verification, diagnosis, repair, SER@k computation, cost ledger,
           results tables — WITHOUT any LLM. All outputs are watermarked
           NOT-REPORTABLE. Use this to prove the machinery works.

  (real)   Requires ANTHROPIC_API_KEY. Pins model versions, runs the actual
           configurations, and writes reportable results. These are the only
           numbers that may ever appear in the manuscript.

Usage:
    python experiments/run_experiments.py --mock
    ANTHROPIC_API_KEY=sk-... python experiments/run_experiments.py \
        --cheap claude-haiku-4-5-20251001 --frontier claude-sonnet-4-6
"""
from __future__ import annotations
import argparse
import json
import re
import os
import sys
from typing import Dict, List

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from etl_transbench.harness import Task, discover_tasks  # noqa: E402
from legato.core import LLMClient, EscalationPolicy, run_legato  # noqa: E402
from legato.mock_llm import MockLLMClient  # noqa: E402

MOCK_BANNER = ("=" * 72 + "\n"
               "  MODE = MOCK  |  HARNESS VALIDATION ONLY\n"
               "  Every number below is produced by a SCRIPTED stand-in model.\n"
               "  These values validate the pipeline and MUST NOT be reported\n"
               "  in any manuscript, talk, or petition material.\n" + "=" * 72)


def sse_at_k(histories: List[List[dict]], k: int) -> float:
    """SER@k: fraction of tasks equivalent within k repair iterations."""
    ok = sum(1 for h in histories
             if any(e["class"] == "equivalent" and e["iter"] <= k for e in h))
    return ok / len(histories) if histories else 0.0


def run_config(tasks: List[Task], llm, policy: EscalationPolicy, label: str):
    rows, histories = [], []
    for i, t in enumerate(tasks, 1):
        print(f"  [{label}] {i}/{len(tasks)} {t.meta['id']} ...",
              flush=True)
        res = run_legato(t, llm, policy)
        histories.append(res.history)
        rows.append({"task": res.task_id, "category": t.meta["category"],
                     "equivalent": res.equivalent, "iterations": res.iterations,
                     # Section 6.4 needs the per-iteration diagnosis classes to
                     # build the failure taxonomy; persist them with the row.
                     "history": res.history,
                     "final_class": (res.history[-1]["class"] if res.history
                                     else None),
                     **res.cost})
    return {"config": label,
            "ser_at": {k: round(sse_at_k(histories, k), 4) for k in (0, 1, 3, 5)},
            "total_usd": round(sum(r["usd"] for r in rows), 4),
            "total_tokens": int(sum(r["tokens_in"] + r["tokens_out"] for r in rows)),
            "tasks": rows}


def to_markdown(results: List[dict], mock: bool) -> str:
    lines = []
    if mock:
        lines.append("> **MOCK VALIDATION RUN — NOT REPORTABLE**\n")
    lines.append("| Configuration | SER@0 | SER@1 | SER@3 | SER@5 | Cost (USD) |")
    lines.append("|---|---|---|---|---|---|")
    for r in results:
        s = r["ser_at"]
        cost = f'{r["total_usd"]:.4f}' + (" (scripted)" if mock else "")
        lines.append(f'| {r["config"]} | {s[0]:.2f} | {s[1]:.2f} | {s[3]:.2f} | '
                     f'{s[5]:.2f} | {cost} |')
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--cheap", default="claude-haiku-4-5-20251001")
    ap.add_argument("--frontier", default="claude-sonnet-4-6")
    ap.add_argument("--out", default=os.path.join(ROOT, "experiments", "results"))
    ap.add_argument("--configs", default="",
                    help="comma-separated config numbers to run (e.g. 3). "
                         "Final results are assembled from ALL partial_*.json "
                         "in --out, so interrupted runs can be resumed.")
    ap.add_argument("--tasks", default="",
                    help="comma-separated task ids to run (subset run). "
                         "Subset runs write partial_<TAG>_subset_*.json and are "
                         "NEVER merged into the full-benchmark result file.")
    ap.add_argument("--limit", type=int, default=0,
                    help="run only the first N tasks (smoke test; mark output NOT-FULL)")
    args = ap.parse_args()

    tasks = [Task.load(d) for d in discover_tasks(os.path.join(ROOT, "tasks"))]
    if args.tasks:
        want_ids = {x.strip() for x in args.tasks.split(",") if x.strip()}
        tasks = [t for t in tasks if t.meta["id"] in want_ids]
        missing = want_ids - {t.meta["id"] for t in tasks}
        if missing:
            sys.exit(f"unknown task ids: {sorted(missing)}")
        print(f"SUBSET: {len(tasks)} task(s) — NOT a full-benchmark result.")
    if args.limit:
        tasks = tasks[:args.limit]
        print(f"LIMIT={args.limit}: partial run over {len(tasks)} tasks "
              "— NOT a full-benchmark result.")
    os.makedirs(args.out, exist_ok=True)

    if args.mock:
        print(MOCK_BANNER)
        llm_factory = MockLLMClient            # fresh scripted state per config
        tag = "MOCK_VALIDATION"
    else:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("Real mode requires ANTHROPIC_API_KEY. "
                     "Use --mock for harness validation.")
        llm_factory = lambda: LLMClient(model_cheap=args.cheap,
                                        model_frontier=args.frontier)
        tag = "REAL"
        print(f"REAL RUN | cheap={args.cheap} | frontier={args.frontier}")

    configs = [
        ("B1 single-pass (cheap)", EscalationPolicy(max_iters=0)),
        ("LEGATO full (escalation)", EscalationPolicy()),
        ("Ablation: retranslation without feedback",
         EscalationPolicy(escalate_after=0, retranslate_after=0)),
        ("B3: self-repair without external grounding",
         EscalationPolicy(grounded=False)),
    ]
    if args.configs:
        want = {int(x) for x in args.configs.split(",") if x.strip()}
        configs = [c for i, c in enumerate(configs, 1) if i in want]
        print(f"RESUME: running only config(s) {sorted(want)}")
        idx_map = sorted(want)
    else:
        idx_map = list(range(1, len(configs) + 1))

    results = []
    for label, pol in configs:
        r = run_config(tasks, llm_factory(), pol, label)
        results.append(r)
        cfg_idx = idx_map[len(results) - 1]
        subset = bool(args.tasks or args.limit)
        stem = f"partial_{tag}_subset_{cfg_idx}" if subset else f"partial_{tag}_{cfg_idx}"
        part = os.path.join(args.out, stem + ".json")
        with open(part, "w") as f:
            json.dump({"mode": tag, "config_index": cfg_idx,
                       "models": (None if args.mock else
                                  {"cheap": args.cheap,
                                   "frontier": args.frontier}),
                       "result": r}, f, indent=2)
        print(f"  -> wrote {part}", flush=True)

    # Assemble the final report from every partial on disk, so a resumed
    # run composes with configs completed in an earlier invocation.
    subset_run = bool(args.tasks or args.limit)
    pat = (rf"partial_{tag}_subset_\d+\.json" if subset_run
           else rf"partial_{tag}_\d+\.json")
    merged = {}
    for fn in os.listdir(args.out):
        if re.fullmatch(pat, fn):
            with open(os.path.join(args.out, fn)) as f:
                d = json.load(f)
            r = d["result"]
            # JSON round-trip stringifies the integer SER@k keys
            r["ser_at"] = {int(k): v for k, v in r["ser_at"].items()}
            merged[d["config_index"]] = r
    results = [merged[k] for k in sorted(merged)]
    print(f"assembled {len(results)} config(s) from partials")

    payload = {"mode": tag,
               "reportable": tag == "REAL" and not args.limit,
               "n_tasks": len(tasks),
               "limited": bool(args.limit),
               "warning": None if tag == "REAL" else
                          "Scripted validation run. Numbers are meaningless.",
               "models": (None if args.mock else
                          {"cheap": args.cheap, "frontier": args.frontier}),
               "results": results}
    stem_out = f"results_{tag}_subset" if subset_run else f"results_{tag}"
    jpath = os.path.join(args.out, stem_out + ".json")
    with open(jpath, "w") as f:
        json.dump(payload, f, indent=2)
    mpath = os.path.join(args.out, stem_out + ".md")
    with open(mpath, "w") as f:
        f.write(to_markdown(results, args.mock) + "\n")

    print(to_markdown(results, args.mock))
    print(f"\nwritten: {jpath}\n         {mpath}")
    if args.mock:
        print("\nPipeline validated. To produce reportable results:\n"
              "  ANTHROPIC_API_KEY=... python experiments/run_experiments.py")


if __name__ == "__main__":
    main()
