"""Generate the cost-SER Pareto figure (paper headline figure) from a results
JSON. Mock-mode inputs produce a figure stamped NOT REPORTABLE."""
import json, sys, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = sys.argv[1] if len(sys.argv) > 1 else "experiments/results/results_REAL.json"
with open(path) as f:
    data = json.load(f)
fig, ax = plt.subplots(figsize=(6, 4.2))
for r in data["results"]:
    ser5 = r["ser_at"].get("5", r["ser_at"].get(5, list(r["ser_at"].values())[-1]))
    ax.scatter(r["total_usd"], ser5, s=70, label=r["config"])
ax.set_xlabel("Total cost (USD)"); ax.set_ylabel("SER@5")
ax.set_title("Cost vs. semantic equivalence rate")
ax.legend(fontsize=8); ax.grid(alpha=0.3)
if not data.get("reportable"):
    fig.text(0.5, 0.5, "MOCK VALIDATION\nNOT REPORTABLE", fontsize=28, color="red",
             alpha=0.30, ha="center", va="center", rotation=20)
out = path.replace(".json", "_pareto.png")
fig.savefig(out, dpi=200, bbox_inches="tight"); print("written:", out)
