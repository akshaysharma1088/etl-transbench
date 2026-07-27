# Measured run, 26 July 2026

Reported in the paper. Do not edit these files; add new runs as sibling
directories so results stay traceable to a date and configuration.

**Models:** `claude-haiku-4-5-20251001` (cheap tier), `claude-sonnet-5` (frontier tier)
**Scope:** 32 base tasks, 4 configurations, 128 task runs
**Total cost:** USD 5.09  **Wall clock:** ~50 min

| File | Contents |
|---|---|
| `results_REAL.json` | Merged report, all four configurations |
| `results_REAL.md` | Summary table |
| `partial_REAL_1.json` | B1 single-pass, per-task detail |
| `partial_REAL_2.json` | LEGATO grounded repair, per-task detail |
| `partial_REAL_3.json` | Ablation, retranslation without feedback |
| `partial_REAL_4.json` | B3, self-repair without external grounding |
| `fig_legato_pareto.png` | SER@k curves and cost-accuracy plane |

Each per-task record carries `equivalent`, `iterations`, `tokens_in`,
`tokens_out`, `usd`, and `wall_s`, so the cost accounting in the paper can be
recomputed from source.

## Provenance notes

Three things a careful reader should know.

**A stale configuration label.** `partial_REAL_3.json` records the config name
as `"Ablation: frontier-everywhere"`. That was an early, inaccurate label for
what the paper calls *retranslation without feedback*. It is the same
configuration: identical initial tier selection and iteration budget, differing
only in that each iteration discards the verification evidence and
re-translates at the frontier tier. The label is preserved as written by the
run rather than edited after the fact, since these are measurement artifacts.

The remaining two are discussed in the paper's threats section.

**The retranslation ablation was executed twice.** The first run solved 24 of
32 at USD 1.601; the second solved 25 of 32 at USD 1.473. The second is the one
reported here and in the paper. The first was overwritten during a resumed run
and is not recoverable, but the figures are recorded here and in the manuscript
so the discrepancy is on the record rather than hidden.

**SER@0 is not identical across the three repair configurations** (0.656,
0.656, 0.625) even though they share an identical initial-translation policy
and should therefore agree exactly. The 0.031 spread is one task of sampling
noise.

Taken together these two observations put run-to-run variance at about one
task. That is well below the 0.125 gap between grounded and ungrounded repair,
but it is the same size as any apparent difference *within* the ungrounded
pair, which is why the paper claims no difference between them in equivalence
rate.
