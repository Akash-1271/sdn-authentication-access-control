"""Regenerate the report figure from the unchanged measured CSV (matplotlib)."""
import csv
import hashlib
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "data/performance_results_current.csv"
with source.open(newline="", encoding="utf-8") as stream:
    rows = list(csv.DictReader(stream))
values = {mode: [float(row["service_rtt_ms"]) for row in rows if row["mode"] == mode]
          for mode in ("dynamic", "static")}
assert all(len(group) == 20 for group in values.values())

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                     "svg.fonttype": "none", "svg.hashsalt": "sdn-final-20261029", "axes.spines.top": False,
                     "axes.spines.right": False})
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={"width_ratios": [1.5, 1]})
colors = {"dynamic": "#007f86", "static": "#b65c19"}
for mode, data in values.items():
    axes[0].plot(range(1, 21), data, marker="o", markersize=5, linewidth=1,
                 label=mode.capitalize(), color=colors[mode])
axes[0].set(title="Every service transaction (all samples retained)",
            xlabel="Trial within each mode", ylabel="Service transaction time (ms, log scale)")
axes[0].set_xticks([1, 5, 10, 15, 20])
axes[0].legend(frameon=False, loc="upper left")

for i, (mode, data) in enumerate(values.items()):
    mean, median = statistics.mean(data), statistics.median(data)
    axes[1].bar(i - .18, mean, .32, color=colors[mode], label="Mean" if i == 0 else None)
    axes[1].bar(i + .18, median, .32, color=colors[mode], alpha=.4,
                label="Median" if i == 0 else None)
    for x, y in [(i - .18, mean), (i + .18, median)]:
        axes[1].text(x, y * 1.15, f"{y:.2f}", ha="center", fontsize=10)
axes[1].set(title="Mean and median describe different features",
            ylabel="Service transaction time (ms, log scale)")
axes[1].set_xticks([0, 1], ["Dynamic", "Static"])
axes[1].legend(frameon=False, loc="upper right")
for ax in axes:
    ax.set_yscale("log")
    ax.set_ylim(.5, 2000)
    ax.set_yticks([1, 10, 100, 1000])
    ax.yaxis.set_major_formatter(ScalarFormatter())
    ax.grid(axis="y", which="major", alpha=.2)
    ax.set_axisbelow(True)
fig.suptitle("Dynamic authentication vs static permission | 20 trials per mode", fontsize=15, weight="bold")
fig.text(.5, .025, "29 October 2026 VM batch | TCP setup + request/reply | Login measured separately | No samples discarded",
         ha="center", fontsize=10, color="#475569")
fig.tight_layout(rect=[0, .065, 1, .94])
digest = hashlib.sha256(source.read_bytes()).hexdigest()
fig.savefig(ROOT / "data/performance-comparison.svg", metadata={"Date": None, "Description": "Input CSV SHA-256: " + digest})
output = ROOT / "data/performance-comparison.svg"
output.write_text("\n".join(line.rstrip() for line in output.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
plt.close(fig)
print("Created performance-comparison.svg from CSV " + digest)
