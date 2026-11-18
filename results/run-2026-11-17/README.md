# Measured run, 17 November 2026 (revised protocol)

Produced by `experiments/run_v2.py`, summarised by `experiments/analyze_v2.py`.

**Models:** `claude-haiku-4-5-20251001` (cheap tier), `claude-sonnet-5` (frontier tier; the API reported no dated snapshot)
**Sampling:** API default temperature (1.0), max 4,000 output tokens
**Scope:** 32 tasks, 6 configurations, 5 repetitions (960 task runs)
**Corpora:** repair uses development seeds 11, 23, 47; scoring uses held-out seeds 101, 211, 307, 401, 503. Repetition r adds 1000 × r to every seed.
**Total cost:** about USD 39 at the prices in `manifest.json`

Within a repetition, every configuration in one initial-translation group starts from the same first candidate (`rep*/initial/`). See `summary.md` for the tables and `summary.json` for the raw figures.
