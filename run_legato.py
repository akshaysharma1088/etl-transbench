"""CLI: run the LEGATO loop on one task. Requires ANTHROPIC_API_KEY."""
import json, sys
from etl_transbench.harness import Task
from legato.core import LLMClient, EscalationPolicy, run_legato

if __name__ == "__main__":
    task = Task.load(sys.argv[1])
    llm = LLMClient(model_cheap="claude-haiku-4-5-20251001",
                    model_frontier="claude-sonnet-4-6")  # pin exact versions for paper runs
    res = run_legato(task, llm, EscalationPolicy())
    print(json.dumps({"task": res.task_id, "equivalent": res.equivalent,
                      "iterations": res.iterations, "cost": res.cost,
                      "history": res.history}, indent=2, default=str))
    if not res.equivalent and res.handoff:
        print("\n--- HUMAN HANDOFF PACKAGE ---")
        print(json.dumps(res.handoff["failure_report"], indent=2, default=str)[:3000])
