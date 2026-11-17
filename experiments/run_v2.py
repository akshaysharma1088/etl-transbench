"""Experiment runner for the revised protocol (repeated runs, held-out scoring).

What differs from run_experiments.py:

  * Every configuration is run --reps times. Repetition r draws its corpora
    from its own seeds, and each repetition makes fresh model calls.
  * Within a repetition, all configurations that share an initial-translation
    setting start from the SAME first candidate, generated once and stored.
    Differences between them then come from the repair strategy alone.
  * The repair loop verifies against development corpora. The reported score
    is computed on held-out corpora that never reach a prompt.
  * Results are written per task, so an interrupted run resumes without
    paying twice. Token counts are stored per call tier, so cost can be
    recomputed under any price table.

Usage:
    python experiments/run_v2.py --mock --reps 2 --out /tmp/mock_v2
    ANTHROPIC_API_KEY=... python experiments/run_v2.py --out results/run-v2
    python experiments/analyze_v2.py results/run-v2
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from etl_transbench.harness import (Task, CostLedger, compile_candidate,  # noqa: E402
                                    discover_tasks, verify_candidate)
from legato.core import (LLMClient, EscalationPolicy, PRICES_USD_PER_MTOK,  # noqa: E402
                         TRANSLATOR_SYSTEM, REPAIR_SYSTEM, CONSTRUCT_HINTS,
                         initial_translation, run_legato)
from legato.mock_llm import MockLLMClient  # noqa: E402

DEV_SEEDS = (11, 23, 47)                 # shown to the repair loop
HELDOUT_SEEDS = (101, 211, 307, 401, 503)  # used for scoring only
REP_STRIDE = 1000                        # repetition r adds r * REP_STRIDE to both

# name -> (policy, initial-translation group). Configurations in one group
# start from the same first candidate.
CONFIGS = {
    "B1_single_pass":      (EscalationPolicy(max_iters=0), "default"),
    "LEGATO":              (EscalationPolicy(), "default"),
    "B2_retranslate":      (EscalationPolicy(escalate_after=0, retranslate_after=0), "default"),
    "B3_self_repair":      (EscalationPolicy(grounded=False), "default"),
    "A1_trace_only":       (EscalationPolicy(evidence="trace_only"), "default"),
    "A2_no_hints":         (EscalationPolicy(use_hints=False), "no_hints"),
    "A3_frontier_only":    (EscalationPolicy(fixed_tier="frontier"), "frontier"),
    "A4_cheap_only":       (EscalationPolicy(fixed_tier="cheap"), "cheap"),
}
DEFAULT_CONFIGS = "B1_single_pass,LEGATO,B2_retranslate,B3_self_repair,A1_trace_only,A2_no_hints"


def seeds_for(rep: int):
    return ([s + rep * REP_STRIDE for s in DEV_SEEDS],
            [s + rep * REP_STRIDE for s in HELDOUT_SEEDS])


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, default=str)
    os.replace(tmp, path)


def get_initial(task, llm, policy, group, rep_dir):
    """The shared first candidate for (repetition, group, task), made once."""
    path = os.path.join(rep_dir, "initial", group, task.meta["id"] + ".json")
    if os.path.exists(path):
        return load_json(path)
    ledger = CostLedger()
    code = initial_translation(task, llm, policy, ledger)
    rec = {"task": task.meta["id"], "group": group,
           "tier": policy.initial_tier(task), "code": code, "calls": ledger.entries}
    save_json(path, rec)
    return rec


def run_one(task, llm, name, rep, out):
    policy, group = CONFIGS[name]
    rep_dir = os.path.join(out, f"rep{rep}")
    path = os.path.join(rep_dir, name, task.meta["id"] + ".json")
    if os.path.exists(path):
        return load_json(path)
    dev, held = seeds_for(rep)
    init = get_initial(task, llm, policy, group, rep_dir)
    res = run_legato(task, llm, policy, initial_code=init["code"],
                     dev_seeds=dev, heldout_seeds=held)
    # The first candidate is also scored on held-out corpora, so SER@0 can be
    # reported there too.
    fn, _ = compile_candidate(init["code"])
    first_ok = bool(fn) and verify_candidate(task, fn, seeds=tuple(held)).equivalent
    rec = {"config": name, "rep": rep, "task": res.task_id,
           "category": task.meta["category"],
           "dev_equivalent": res.equivalent, "iterations": res.iterations,
           "heldout_equivalent": res.heldout_equivalent,
           "heldout_equivalent_first": first_ok,
           "history": res.history, "final_code": res.final_code,
           "initial_calls": init["calls"],   # shared across the group; counted once per config
           "repair_cost": res.cost,
           "dev_seeds": dev, "heldout_seeds": held}
    save_json(path, rec)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--cheap", default="claude-haiku-4-5-20251001")
    ap.add_argument("--frontier", default="claude-sonnet-5")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--configs", default=DEFAULT_CONFIGS,
                    help=f"comma-separated, from: {', '.join(CONFIGS)}")
    ap.add_argument("--tasks", default="", help="comma-separated task ids (default: all)")
    ap.add_argument("--workers", type=int, default=4, help="tasks run in parallel")
    ap.add_argument("--temperature", type=float, default=None,
                    help="sampling temperature (default: the API default, 1.0)")
    ap.add_argument("--prices", default="", help="JSON file: {tier: {in, out}} in USD per million tokens")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    names = [c.strip() for c in args.configs.split(",") if c.strip()]
    unknown = [n for n in names if n not in CONFIGS]
    if unknown:
        sys.exit(f"unknown configs: {unknown}")
    tasks = [Task.load(d) for d in discover_tasks(os.path.join(ROOT, "tasks"))]
    if args.tasks:
        want = {x.strip() for x in args.tasks.split(",")}
        tasks = [t for t in tasks if t.meta["id"] in want]
    prices = load_json(args.prices) if args.prices else PRICES_USD_PER_MTOK

    if args.mock:
        print("MOCK run: scripted model, numbers are not reportable.")
    elif not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Real mode requires ANTHROPIC_API_KEY. Use --mock to test the pipeline.")

    os.makedirs(args.out, exist_ok=True)
    shared = None if args.mock else LLMClient(args.cheap, args.frontier,
                                              temperature=args.temperature, prices=prices)
    t0 = time.time()
    for rep in range(args.reps):
        # The mock keeps a per-task call counter, so it needs fresh state per
        # configuration; the real client is stateless and shared.
        for name in names:
            llm = MockLLMClient() if args.mock else shared
            workers = 1 if args.mock else args.workers
            with ThreadPoolExecutor(max_workers=workers) as pool:
                recs = list(pool.map(lambda t: run_one(t, llm, name, rep, args.out), tasks))
            solved = sum(bool(r["heldout_equivalent"]) for r in recs)
            print(f"rep {rep} {name:18s} held-out solved {solved}/{len(recs)} "
                  f"[{time.time() - t0:.0f}s]", flush=True)

    manifest = {
        "mode": "MOCK" if args.mock else "REAL",
        "models_requested": None if args.mock else {"cheap": args.cheap, "frontier": args.frontier},
        "models_resolved": None if args.mock else shared.resolved,
        "temperature": "API default (1.0)" if args.temperature is None else args.temperature,
        "max_tokens": 4000, "prices_usd_per_mtok": prices,
        "reps": args.reps, "configs": names, "n_tasks": len(tasks),
        "dev_seeds": DEV_SEEDS, "heldout_seeds": HELDOUT_SEEDS, "rep_stride": REP_STRIDE,
        "policies": {n: asdict(CONFIGS[n][0]) for n in names},
        "initial_groups": {n: CONFIGS[n][1] for n in names},
        "prompts": {"translator_system": TRANSLATOR_SYSTEM, "repair_system": REPAIR_SYSTEM,
                    "construct_hints": CONSTRUCT_HINTS},
    }
    save_json(os.path.join(args.out, "manifest.json"), manifest)
    print(f"done. Next: python experiments/analyze_v2.py {args.out}")


if __name__ == "__main__":
    main()
