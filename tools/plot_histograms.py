#!/usr/bin/env python3
"""Plot observed and crop/recompression-estimate AC-coefficient histograms.

Run from the challenge root:
    python tools/plot_histograms.py
Requires numpy and matplotlib. The CSV data are provided, so jpeg libraries are
not needed for this analysis step.
"""
from pathlib import Path
import csv
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "evidence" / "histograms" / "observed"
EST = ROOT / "evidence" / "histograms" / "recompressed_estimate"
OUT = ROOT / "histogram_comparison.png"
CANDIDATES = ["img_0147", "img_0213", "img_0388", "img_0412"]
MAX_MAG = 15

def read_hist(path):
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    raw = {r["value"]: int(r["count"]) for r in rows}
    total = raw["TOTAL"]
    signed = {k: raw.get(str(k), 0) / total for k in range(-20, 21)}
    absolute = np.array([
        signed[0] if m == 0 else signed[m] + signed[-m]
        for m in range(MAX_MAG + 1)
    ])
    return absolute

def main():
    fig, axes = plt.subplots(4, 2, figsize=(12, 13), constrained_layout=True)
    x = np.arange(MAX_MAG + 1)
    for i, candidate in enumerate(CANDIDATES):
        observed = read_hist(OBS / f"{candidate}.csv")
        estimated = read_hist(EST / f"{candidate}.csv")
        ax = axes[i, 0]
        ax.plot(x, observed, marker="o", markersize=3, linewidth=1.2, label="Observed JPEG")
        ax.plot(x, estimated, marker="s", markersize=3, linewidth=1.2, label="Crop + recompress estimate")
        ax.set_title(candidate)
        ax.set_xlabel(r"Absolute quantized Y AC coefficient $|c|$")
        ax.set_ylabel("Fraction of all Y AC positions")
        ax.grid(True, alpha=.25)
        if i == 0:
            ax.legend(fontsize=8)
        d = observed - estimated
        ax2 = axes[i, 1]
        ax2.axhline(0, linewidth=0.8, color="black")
        ax2.bar(x, d, width=0.8)
        ax2.set_title(f"Observed minus estimate: {candidate}")
        ax2.set_xlabel(r"Absolute quantized Y AC coefficient $|c|$")
        ax2.set_ylabel("Difference in probability mass")
        ax2.grid(True, axis="y", alpha=.25)
    fig.suptitle("Garden Gallery: quantized JPEG luminance AC-coefficient statistics", fontsize=14)
    fig.savefig(OUT, dpi=170)
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
