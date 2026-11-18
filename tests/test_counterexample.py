"""The counterexample builder and the patch-then-fresh strategy.

No model is called: a scripted client returns a planted-defect program, then
the same defect again, then the oracle, and records the prompts it was sent.
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
from etl_transbench.harness import Task, compile_candidate  # noqa: E402
from legato import counterexample  # noqa: E402
from legato.core import EscalationPolicy, run_legato  # noqa: E402

TID = "t5h_scd2_surrogate_pit"
task = Task.load(os.path.join(ROOT, "tasks", TID))
with open(os.path.join(task.task_dir, "reference.py")) as f:
    GOOD = f.read()
BAD = GOOD.replace('f["txn_date"] < r["eff_end_date"]', 'f["txn_date"] <= r["eff_end_date"]')
assert BAD != GOOD

# 1. The builder shows the failing fact row, both outputs, and the dimension
#    rows reached through customer_id.
fn, _ = compile_candidate(BAD)
cx = counterexample.build(task, fn, 11)
case = cx["relations"][0]["cases"][0]
assert cx["relations"][0]["relation"] == "fact_txn_keyed"
assert case["legacy_system_produced"] != case["your_code_produced"]
assert "fact_txn" in case["input_rows"] and "dim_customer" in case["input_rows"]
assert len(cx["relations"][0]["cases"]) <= counterexample.MAX_KEYS
# A correct program has no counterexample.
good_fn, _ = compile_candidate(GOOD)
assert counterexample.build(task, good_fn, 11) is None
print("PASS  builder: failing key, both outputs and related input rows; nothing for a correct program")


class Scripted:
    """Returns the scripted replies in order and keeps the prompts."""
    def __init__(self, replies):
        self.replies, self.prompts = list(replies), []

    def complete(self, tier, system, user, ledger, role, max_tokens=0):
        self.prompts.append((role, user))
        ledger.record(role, "scripted", 0, 0, 0.0, 0.0)
        return "```python\n" + self.replies.pop(0) + "```"


# 2. Patch first with a counterexample; when the patch fails, translate afresh
#    with the evidence and without the failed code.
llm = Scripted([BAD, GOOD])
policy = EscalationPolicy(fixed_tier="cheap", evidence="counterexample", strategy="patch_then_fresh")
res = run_legato(task, llm, policy, initial_code=BAD, dev_seeds=[11, 23], heldout_seeds=[101, 211])
assert res.equivalent and res.heldout_equivalent and res.iterations == 2, res.history
(role1, p1), (role2, p2) = llm.prompts
assert role1 == "repair" and "PREVIOUS CODE" in p1 and "legacy_system_produced" in p1
assert role2 == "translator" and "PREVIOUS CODE" not in p2 and "legacy_system_produced" in p2
assert "FAILED" in p2
print("PASS  loop: patch with a counterexample, then a fresh translation that carries the evidence")

# 3. Nothing from the held-out corpora reaches a prompt.
held = task.corpus(101)["fact_txn"]
dev_ids = set(task.corpus(11)["fact_txn"]["amount"]) | set(task.corpus(23)["fact_txn"]["amount"])
only_held = [a for a in held["amount"] if a not in dev_ids][:50]
assert only_held and not any(repr(a) in p1 + p2 for a in only_held)
print("PASS  no held-out value appears in any prompt")

# 4. The submitted configuration is unchanged: summary evidence, patches only.
llm = Scripted([BAD, BAD, BAD, BAD])
res = run_legato(task, llm, EscalationPolicy(fixed_tier="cheap"), initial_code=BAD, dev_seeds=[11])
assert all("legacy_system_produced" not in p for _, p in llm.prompts)
assert all(role == "repair" for role, _ in llm.prompts[:2])
print("PASS  the first-submission configuration sends summary evidence only")
print("\nALL COUNTEREXAMPLE TESTS PASSED")
