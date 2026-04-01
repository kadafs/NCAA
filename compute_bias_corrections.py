"""
compute_bias_corrections.py
============================
Reads all graded basketball prediction files, computes the average signed delta
(model_total - actual_total) per league, and writes a '_bias_correction' field
into each league's configs/leagues/{id}.json.

The engine will subtract this value from stats_total before finalisation,
directly correcting systematic overshoot/undershoot patterns.

Run after every ~2 weeks of accumulated graded data:
    python compute_bias_corrections.py

Options:
    --min_games N     Minimum graded games required (default: 5)
    --dry_run         Print corrections without writing to configs
"""

import os
import glob
import json
import argparse
import math
import sys
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PREDICTIONS_DIR = os.path.join(os.path.dirname(__file__), "data", "basketball")
CONFIGS_DIR     = os.path.join(os.path.dirname(__file__), "configs", "leagues")
TRACKING_EPOCH  = "2026-03-25"   # Ignore predictions before V2 engine launch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min_games", type=int, default=5)
    parser.add_argument("--dry_run",   action="store_true")
    args = parser.parse_args()

    epoch_dt = datetime.strptime(TRACKING_EPOCH, "%Y-%m-%d")

    print("=" * 60)
    print("  BIAS CORRECTION CALCULATOR v1.0")
    print("=" * 60)

    # --- 1. Aggregate signed deltas per league ---
    league_deltas: dict[str, list[float]] = {}
    league_names:  dict[str, str]  = {}

    pred_files = sorted(glob.glob(os.path.join(PREDICTIONS_DIR, "universal_predictions_*.json")))
    for fp in pred_files:
        # Enforce tracking epoch
        date_str = os.path.basename(fp).replace("universal_predictions_", "").replace(".json", "")
        try:
            if datetime.strptime(date_str, "%Y-%m-%d") < epoch_dt:
                continue
        except ValueError:
            continue

        try:
            data = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue

        for p in data.get("predictions", []):
            sd = p.get("signed_delta")
            if sd is None:
                continue
            lid = str(p.get("league_id", ""))
            if not lid:
                continue
            if lid not in league_deltas:
                league_deltas[lid] = []
                league_names[lid]  = p.get("league", "Unknown")
            league_deltas[lid].append(float(sd))

    # --- 2. Compute stats and write corrections ---
    applied   = 0
    skipped   = 0
    total_abs = 0.0

    for lid, deltas in sorted(league_deltas.items(), key=lambda x: -abs(sum(x[1]) / len(x[1]) if x[1] else 0)):
        n   = len(deltas)
        if n < args.min_games:
            skipped += 1
            continue

        avg_delta = sum(deltas) / n
        std_delta = math.sqrt(sum((d - avg_delta) ** 2 for d in deltas) / n) if n > 1 else 0.0

        # Bias correction = the systematic overshoot to subtract from model output
        # Cap at ±15 pts to avoid over-correcting noise from tiny samples
        correction = max(-15.0, min(15.0, round(avg_delta, 2)))

        # Only apply if correction is meaningful (> 1.5 pts) to avoid noise churn
        if abs(correction) < 1.5:
            skipped += 1
            continue

        config_path = os.path.join(CONFIGS_DIR, f"{lid}.json")
        if not os.path.exists(config_path):
            skipped += 1
            continue

        try:
            cfg = json.load(open(config_path, encoding="utf-8"))
        except Exception:
            skipped += 1
            continue

        old_correction = cfg.get("_bias_correction", 0.0)
        cfg["_bias_correction"]      = correction
        cfg["_bias_n_games"]         = n
        cfg["_bias_avg_delta"]       = round(avg_delta, 2)
        cfg["_bias_std_delta"]       = round(std_delta, 2)
        cfg["_bias_computed_at"]     = datetime.now().strftime("%Y-%m-%d")

        direction = "OVER" if avg_delta > 0 else "UNDER"
        change    = f"{old_correction:+.2f} → {correction:+.2f}" if old_correction != correction else f"{correction:+.2f} (no change)"
        print(f"  [{lid:>4}] {league_names.get(lid,'?')[:28]:28} | n={n:3d} | avg={avg_delta:+.1f} ({direction}) | correction={change}")

        if not args.dry_run:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        applied += 1
        total_abs += abs(correction)

    print()
    print(f"  Applied corrections: {applied} leagues")
    print(f"  Skipped (low data):  {skipped} leagues")
    if applied:
        print(f"  Avg abs correction:  {total_abs / applied:.2f} pts")
    print("=" * 60)


if __name__ == "__main__":
    main()
