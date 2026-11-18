"""Every input relation a task's generator produces must be named in the
legacy artifact shown to the translator. Otherwise the translator has to guess
the key it reads from `inputs`, and a wrong guess fails for a reason that has
nothing to do with translation.

t6b_capped_session is exempt: its artifact describes one unnamed event stream
and the generator calls it `events`.
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
from etl_transbench.harness import Task, discover_tasks  # noqa: E402

EXEMPT = {"t6b_capped_session"}

bad = []
for d in discover_tasks(os.path.join(ROOT, "tasks")):
    t = Task.load(d)
    if t.meta["id"] in EXEMPT:
        continue
    art = t.legacy_artifact.lower()
    missing = [n for n in t.corpus(11) if n.lower() not in art]
    if missing:
        bad.append((t.meta["id"], missing))
assert not bad, f"input relations not named in the artifact: {bad}"
print("ALL INPUT RELATIONS ARE NAMED IN THEIR ARTIFACTS")
