# Contributing

The most valuable contribution is a new benchmark task. The bar is deliberately
specific, because a task that cannot distinguish a correct translation from a
plausible wrong one adds noise rather than signal.

## Adding a task

Create `tasks/<task_id>/` containing five files.

**1. `legacy_artifact.{sql,txt,json}`** — the legacy program. Use `.sql` for
dialect SQL, `.txt` for abstracted procedural pseudocode, `.json` for
vendor-neutral component graphs. Do not paste any vendor's proprietary export
format. Comment the semantics that a translator must preserve, especially the
ones that differ from the obvious modern reading.

**2. `reference.py`** — an executable oracle implementing the *legacy*
semantics, exposing `run(inputs) -> dict[str, DataFrame]`. This is ground
truth. Where legacy behaviour is surprising, say so in a comment; the oracle is
documentation as much as code.

**3. `spec.json`** — the equivalence specification: key columns, whether order
is significant, per-column tolerance, and null or whitespace normalization.
Declare the loosest tolerance that is still correct, not the tightest that
happens to pass.

**4. `generator.py`** — a seeded generator exposing `corpus(seed) -> dict[str,
DataFrame]`.

**This is the part that matters.** The generator must *guarantee* the
discriminating cases, not sample and hope. If the construct turns on duplicate
keys, inject duplicates explicitly. If it turns on a boundary, place rows
exactly on it and one unit either side. If it turns on physical ordering,
shuffle the frame before returning it.

Three real examples from this benchmark's development, each a bug that a random
corpus missed entirely:

- A missing window tie-break passed every random corpus, because random
  timestamps essentially never tie within a partition.
- A missing cursor tie-break was hidden by a stable sort until the input frame
  was shuffled.
- A watermark off-by-one was invisible until events landed exactly on the
  boundary.

**5. `task.json`** — metadata: `id`, `category` (T1 through T8), `tier`,
`description`, `legacy_artifact`, `target`.

## Prove the task discriminates

Add a defect probe to `tests/test_t<N>_variants.py`, or create the file. It must:

1. Verify the oracle against itself (catches a broken generator or spec).
2. Plant the classic migration bug for that construct and assert the harness
   rejects it.

A task without a passing defect probe will not be merged. The probe is the
evidence that the task measures something.

Run the full suite before opening a PR:

```bash
python tests/test_harness.py
python tests/test_full_benchmark.py
for f in tests/test_t*_variants.py; do python "$f"; done
```

## Reporting results

If you evaluate another model or framework, please include the exact model
version strings, the seed, the per-task cost ledger, and the number of runs.
Given the roughly one-task run-to-run variance we observe, single-run
comparisons finer than about 0.03 SER are not meaningful.
