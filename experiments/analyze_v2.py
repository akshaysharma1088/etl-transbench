"""Summarise a run_v2.py output directory: means, spread and paired tests.

    python experiments/analyze_v2.py results/run-v2 [--baseline LEGATO]

Writes summary.json and summary.md next to the results. Uses only the
standard library.

Statistics:
  * SER per repetition, then mean and sample standard deviation across
    repetitions, on development and on held-out corpora.
  * Paired comparison with the baseline configuration, task by task:
      - a sign-flip permutation test on the per-task difference in solve rate
        (the task is the unit, so repetitions of one task are not treated as
        independent observations);
      - exact McNemar on the pooled (task, repetition) pairs, for reference.
"""
from __future__ import annotations
import argparse
import json
import os
import random
import statistics as st
import sys
from collections import defaultdict
from math import comb

KS = (0, 1, 3, 5)


def load(run_dir):
    recs = []
    for rep in sorted(d for d in os.listdir(run_dir) if d.startswith("rep")):
        for cfg in sorted(os.listdir(os.path.join(run_dir, rep))):
            if cfg == "initial":
                continue
            folder = os.path.join(run_dir, rep, cfg)
            for fn in sorted(os.listdir(folder)):
                if fn.endswith(".json"):
                    with open(os.path.join(folder, fn)) as f:
                        recs.append(json.load(f))
    return recs


def solved_dev_at(rec, k):
    return any(e["class"] == "equivalent" and e["iter"] <= k for e in rec["history"])


def solved_heldout_at(rec, k):
    """Held-out equivalence of the candidate the loop holds after at most k
    repair iterations. The loop stops on development equivalence, so this is
    known at k=0 (first candidate) and once the loop has ended."""
    if k == 0:
        return bool(rec["heldout_equivalent_first"])
    if rec["iterations"] <= k and rec["dev_equivalent"]:
        return bool(rec["heldout_equivalent"])
    if rec["iterations"] == 0:
        return bool(rec["heldout_equivalent_first"])
    return False  # still failing on development corpora at k: counted unsolved


def cost(rec, prices=None):
    """USD and tokens for one task run, first translation included."""
    calls = rec["initial_calls"]
    usd = sum(c["usd"] for c in calls) + rec["repair_cost"]["usd"]
    tok = (sum(c["tokens_in"] + c["tokens_out"] for c in calls)
           + rec["repair_cost"]["tokens_in"] + rec["repair_cost"]["tokens_out"])
    return usd, tok


def mean_sd(xs):
    return (st.mean(xs), st.stdev(xs) if len(xs) > 1 else 0.0)


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value from the discordant counts."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def signflip_p(diffs, n_perm=20000, seed=0):
    """Two-sided sign-flip permutation test on per-task differences."""
    diffs = [d for d in diffs if d != 0]
    if not diffs:
        return 1.0
    obs = abs(sum(diffs))
    if len(diffs) <= 16:  # exact
        hits = total = 0
        for mask in range(2 ** len(diffs)):
            s = sum(d if mask >> i & 1 else -d for i, d in enumerate(diffs))
            hits += abs(s) >= obs - 1e-12
            total += 1
        return hits / total
    rng = random.Random(seed)
    hits = sum(abs(sum(d if rng.random() < 0.5 else -d for d in diffs)) >= obs - 1e-12
               for _ in range(n_perm))
    return (hits + 1) / (n_perm + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--baseline", default="LEGATO")
    args = ap.parse_args()
    recs = load(args.run_dir)
    if not recs:
        sys.exit("no results found")
    by = defaultdict(lambda: defaultdict(dict))  # config -> rep -> task -> rec
    for r in recs:
        by[r["config"]][r["rep"]][r["task"]] = r
    configs = list(by)
    out = {"configs": {}, "paired_vs_" + args.baseline: {}}

    for cfg in configs:
        reps = by[cfg]
        row = {"reps": len(reps), "n_tasks": len(next(iter(reps.values())))}
        for scope, fn in (("dev", solved_dev_at), ("heldout", solved_heldout_at)):
            for k in KS:
                per_rep = [st.mean(fn(r, k) for r in reps[rep].values()) for rep in reps]
                m, s = mean_sd(per_rep)
                row[f"ser{k}_{scope}"] = {"mean": round(m, 4), "sd": round(s, 4),
                                          "per_rep": [round(x, 4) for x in per_rep]}
        usd = [sum(cost(r)[0] for r in reps[rep].values()) for rep in reps]
        tok = [sum(cost(r)[1] for r in reps[rep].values()) for rep in reps]
        row["usd_per_rep"] = {"mean": round(st.mean(usd), 4), "sd": round(mean_sd(usd)[1], 4)}
        row["tokens_per_rep"] = round(st.mean(tok))
        cats = defaultdict(list)
        for rep in reps:
            for r in reps[rep].values():
                cats[r["category"]].append(bool(r["heldout_equivalent"]))
        row["heldout_solve_rate_by_category"] = {c: round(st.mean(v), 3) for c, v in sorted(cats.items())}
        # Tasks that pass development corpora but fail held-out ones: the size
        # of the overfitting the held-out split exists to catch.
        row["dev_pass_heldout_fail"] = sum(
            r["dev_equivalent"] and not r["heldout_equivalent"]
            for rep in reps for r in reps[rep].values())
        out["configs"][cfg] = row

    if args.baseline in by:
        base = by[args.baseline]
        for cfg in configs:
            if cfg == args.baseline:
                continue
            common = sorted(set(base) & set(by[cfg]))
            tasks = sorted(set.intersection(*[set(base[r]) & set(by[cfg][r]) for r in common]))
            b = c = 0
            diffs = []
            for t in tasks:
                x = [bool(base[r][t]["heldout_equivalent"]) for r in common]
                y = [bool(by[cfg][r][t]["heldout_equivalent"]) for r in common]
                b += sum(xi and not yi for xi, yi in zip(x, y))
                c += sum(yi and not xi for xi, yi in zip(x, y))
                diffs.append(st.mean(x) - st.mean(y))
            out["paired_vs_" + args.baseline][cfg] = {
                "reps": len(common), "tasks": len(tasks),
                "mean_ser_difference": round(st.mean(diffs), 4),
                "tasks_baseline_better": sum(d > 0 for d in diffs),
                "tasks_other_better": sum(d < 0 for d in diffs),
                "signflip_p": round(signflip_p(diffs), 4),
                "pooled_discordant": [b, c],
                "mcnemar_exact_p": round(mcnemar_exact(b, c), 4)}

    with open(os.path.join(args.run_dir, "summary.json"), "w") as f:
        json.dump(out, f, indent=2)

    L = ["| Configuration | SER@0 | SER@1 | SER@3 | SER@5 | SER@5 (dev) | Cost per run (USD) |",
         "|---|---|---|---|---|---|---|"]
    for cfg, row in out["configs"].items():
        cell = lambda key: f'{row[key]["mean"]:.3f} ± {row[key]["sd"]:.3f}'
        L.append(f'| {cfg} | {cell("ser0_heldout")} | {cell("ser1_heldout")} | {cell("ser3_heldout")} | '
                 f'{cell("ser5_heldout")} | {cell("ser5_dev")} | '
                 f'{row["usd_per_rep"]["mean"]:.2f} ± {row["usd_per_rep"]["sd"]:.2f} |')
    n = next(iter(out["configs"].values()))
    L.append(f'\nHeld-out SER, mean ± sample SD over {n["reps"]} repetitions of {n["n_tasks"]} tasks.\n')
    if out["paired_vs_" + args.baseline]:
        L += [f"| {args.baseline} vs | Mean SER difference | Tasks better / worse | Sign-flip p | McNemar p (pooled) |",
              "|---|---|---|---|---|"]
        for cfg, p in out["paired_vs_" + args.baseline].items():
            L.append(f'| {cfg} | {p["mean_ser_difference"]:+.3f} | {p["tasks_baseline_better"]} / '
                     f'{p["tasks_other_better"]} | {p["signflip_p"]:.4f} | {p["mcnemar_exact_p"]:.4f} |')
    L += ["", "| Configuration | " + " | ".join(sorted(n["heldout_solve_rate_by_category"])) + " |",
          "|---|" + "---|" * len(n["heldout_solve_rate_by_category"])]
    for cfg, row in out["configs"].items():
        L.append(f"| {cfg} | " + " | ".join(f"{v:.2f}" for _, v in sorted(row["heldout_solve_rate_by_category"].items())) + " |")
    md = "\n".join(L) + "\n"
    with open(os.path.join(args.run_dir, "summary.md"), "w") as f:
        f.write(md)
    print(md)


if __name__ == "__main__":
    main()
