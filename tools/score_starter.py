#!/usr/bin/env python3
"""Optional starter: implement one small histogram-comparison score.

Run with: python tools/score_starter.py
This is a teaching diagnostic, not a general-purpose steganography detector.
"""
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "evidence" / "histograms" / "observed"
EST = ROOT / "evidence" / "histograms" / "recompressed_estimate"
CANDIDATES = ["img_0147", "img_0213", "img_0388", "img_0412"]
MAX_MAGNITUDE = 15


def load_abs_hist(path):
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    raw = {r["value"]: int(r["count"]) for r in rows}
    total = raw["TOTAL"]
    return [
        raw["0"] / total if m == 0
        else (raw[str(m)] + raw[str(-m)]) / total
        for m in range(MAX_MAGNITUDE + 1)
    ]


def discrepancy(observed, estimate):
    # TODO: return the L1 distance between the two probability histograms:
    # sum(abs(observed[m] - estimate[m]) for m = 0,...,MAX_MAGNITUDE)
    # Hint: Python's sum(...) and abs(...) are enough.
    raise NotImplementedError("Complete the one-line histogram discrepancy")


def main():
    scores = []
    for name in CANDIDATES:
        obs = load_abs_hist(OBS / f"{name}.csv")
        est = load_abs_hist(EST / f"{name}.csv")
        scores.append((name, discrepancy(obs, est)))
    for name, score in sorted(scores, key=lambda item: item[1], reverse=True):
        print(f"{name}: {score:.6f}")
    print("Treat this ranking as one piece of evidence, not a verdict.")


if __name__ == "__main__":
    main()
