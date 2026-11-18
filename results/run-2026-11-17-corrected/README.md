# Measured run, 17 November 2026 (corrected protocol)

This is the run to report. It replaces the two earlier runs of the same day
(see `../SUPERSEDED.md`).

Produced by `experiments/run_v2.py`, summarised by `experiments/analyze_v2.py`
(`summary.md` for all 40 tasks, `summary_core.md` for the 32 core tasks,
`summary_extension.md` for the 8 extension tasks).

**Models:** `claude-haiku-4-5-20251001` (cheap tier), `claude-sonnet-5` (frontier tier; the API reported no dated snapshot)
**Sampling:** API default temperature (1.0); output cap 16,000 tokens per call with one retry at double. 13 frontier replies reached the cap and were retried.
**Scope:** 40 tasks, 11 configurations, 5 repetitions (2,200 task runs)
**Corpora:** repair uses development seeds 11, 23, 47; scoring uses held-out seeds 101, 211, 307, 401, 503. Repetition r adds 1000 × r to every seed.
**Prompt:** states the keys and columns of the input dictionary.
**Environment:** Python 3.12.5, pandas 3.1.1
**Total cost:** about USD 25 at the prices in `manifest.json`

Within a repetition, every configuration in one initial-translation group
starts from the same first candidate (`rep*/initial/`).
