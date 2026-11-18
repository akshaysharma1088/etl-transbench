# Runs kept for the record, not for reporting

`run-2026-11-17` and `run-2026-11-17b` were made before two harness defects
were found. Their numbers must not be reported.

1. **The prompt did not state the input dictionary keys.** Legacy artifacts
   write table names in upper case; the harness passes lower-case keys. First
   translations read `inputs["DIM_CUSTOMER"]` and failed with a `KeyError`.
   A repair loop that is shown the error trace fixes this in one step; a loop
   that is not shown it cannot. Most of the measured gap between grounded and
   ungrounded repair in these runs comes from this, not from translation.
2. **Replies were capped at 4,000 output tokens, reasoning included.** The
   frontier model sometimes used the whole cap before writing any code, and
   the empty reply was scored as a failed translation.

Both are fixed in `legato/core.py` (the prompt now lists the input keys and
columns; the cap is 16,000 with one retry, and cut-off replies are counted).
