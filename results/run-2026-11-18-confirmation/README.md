# Confirmation run, 18 November 2026

The single run described in `../CONFIRMATION_PLAN.md`, made with the code at
commit `1cdd734`, which is the commit that added the plan and the tasks.
Nothing was changed between that commit and the run, and no task was changed
or dropped afterwards.

**Scope:** 10 confirmation tasks, 10 configurations, 5 repetitions (500 task runs)
**Models:** `claude-haiku-4-5-20251001` (cheap tier), `claude-sonnet-5` (frontier tier)
**Total cost:** about USD 7.50. Six frontier replies reached the output cap and were retried.

## Result

Held-out SER after the loop, mean over 5 repetitions of 10 tasks:

| Default tiers | SER | | Cheap model only | SER |
|---|---|---|---|---|
| Single pass | 0.94 | | Single pass | 0.80 |
| Retranslate | 1.00 | | Retranslate | 0.88 |
| Self-repair, no evidence | 0.96 | | Self-repair, no evidence | 0.92 |
| Summary evidence (`LEGATO`) | 0.98 | | Summary evidence | 0.92 |
| Counterexample evidence (`L1`) | 1.00 | | Counterexample evidence | 0.90 |

**No planned comparison reaches significance.** Every sign-flip test over
tasks gives p = 1.00, except SER after one repair for counterexamples against
retranslation on the cheap model (0.90 against 0.84, p = 0.25).

The tasks were meant to be hard and were not: the default-tier single pass
solved 47 of 50 runs, so only three first-pass failures were left for any
repair method to work on, all on one task (`t8f_positions_versioned_cdc`).
On those three, repair with counterexamples cost USD 0.09 per failure,
retranslation 0.25, self-repair 0.46 and summary evidence 0.60. Three
failures cannot support a claim.

## One translation passed the repair data and failed the held-out data

In repetition 4 the cheap model's first translation of
`t8i_snapshot_diff_changelog` decided whether a key existed in a snapshot by
testing whether all of its data columns were NULL. A row whose price, stock
and label are all NULL is then read as a missing key. No development corpus
of that repetition contained such a row with a change; held-out corpus 4503
did. The five cheap configurations share that first translation, so the one
program accounts for all five runs counted under `dev_pass_heldout_fail`.
This is the only such program in 3,900 task runs across this run and
`../run-2026-11-17-corrected`.
