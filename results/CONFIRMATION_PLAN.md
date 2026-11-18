# Confirmation run: plan, written before the run

Committed on 17 November 2026, before any model was run on the confirmation
tasks. Its purpose is to test, on tasks that played no part in designing the
method, whether repair guided by counterexamples does better than repair
without them.

## Why a separate set

Counterexample evidence (`legato/counterexample.py`) was designed while looking
at results on the 40 core and extension tasks. Those tasks are therefore
development data for that feature. The 10 confirmation tasks
(`"set": "confirmation"` in `tasks/*/task.json`) were written afterwards, by
hand, without running any model on them. They are stateful by design:
running balances, lot matching, allocation waterfalls, versioned change
capture, and three tasks that are also checked on a replay pass.

## What is run

`experiments/run_v2.py --set confirmation`, 5 repetitions, held-out scoring,
shared first translations within each group, the settings of
`results/run-2026-11-17-corrected`.

| Family | Configurations |
|---|---|
| Default tiers | `B1_single_pass`, `B2_retranslate`, `B3_self_repair`, `LEGATO` (summary evidence), `L1_counterexample` |
| Cheap model only | `C0_cheap_single`, `C2_cheap_retranslate`, `C3_cheap_self_repair`, `C1_cheap_grounded` (summary evidence), `C5_cheap_counterexample` |

## Outcomes

For `L1_counterexample` against `B2_retranslate`, `B3_self_repair` and `LEGATO`,
and for `C5_cheap_counterexample` against `C2`, `C3` and `C1`:

1. **Held-out SER after the loop** (SER@5).
2. **Held-out SER after at most one repair** (SER@1).
3. **Repair cost per first-pass failure**, in USD.

The unit of analysis is the task: each task contributes its mean over the 5
repetitions. Differences are tested with a two-sided sign-flip permutation
test over the 10 tasks, at 0.05, without correction; all comparisons are
reported whether or not they reach it. With 10 tasks the test has little
power, and a null result will be reported as such.

## Rules fixed in advance

- All results are reported, including any in which counterexamples do worse.
- No task is dropped for being too easy or too hard.
- A task is changed only if a defect in the task itself is shown: its oracle
  contradicts its artifact, or the prompt lacks information the translation
  needs. Any such change is described, and the task is rerun for every
  configuration.
- No further change is made to the method between this commit and the run.
