"""
backtest_v4.py
==============
Backtest v4.0 engine changes against historical predictions with actual results.
Computes MAE (Mean Absolute Error) for totals predictions.

Usage:
    python backtest_v4.py
"""

import os
import sys
import json
import math

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

DATA_DIR = "data/basketball"


def load_predictions_with_actuals():
    """Load all historical predictions that have actual results graded."""
    all_games = []
    files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith("universal_predictions_") and f.endswith(".json")])
    
    for fn in files:
        fp = os.path.join(DATA_DIR, fn)
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        
        preds = data.get("predictions", [])
        for p in preds:
            actual = p.get("actual_result")
            model_total = p.get("model_total")
            if not actual or not model_total:
                continue
            
            # actual_result can be a dict with actual_total, or a string
            actual_total = None
            if isinstance(actual, dict):
                actual_total = actual.get("actual_total")
            elif isinstance(actual, str):
                # Try to extract total from string like "HOME 85-72"
                import re
                m = re.search(r'(\d+)\s*-\s*(\d+)', actual)
                if m:
                    actual_total = int(m.group(1)) + int(m.group(2))
            
            if actual_total and model_total:
                all_games.append({
                    "date": data.get("date", fn),
                    "away": p.get("away", "?"),
                    "home": p.get("home", "?"),
                    "league": p.get("league", "?"),
                    "league_id": p.get("league_id"),
                    "model_total": float(model_total),
                    "actual_total": float(actual_total),
                    "error": float(model_total) - float(actual_total),
                    "abs_error": abs(float(model_total) - float(actual_total)),
                })
    
    return all_games


def main():
    print("\n" + "=" * 70)
    print("  BACKTEST v4.0 — Historical Prediction Accuracy")
    print("=" * 70)
    
    games = load_predictions_with_actuals()
    
    if not games:
        print("  No graded predictions found. Run grading scripts first.")
        return
    
    # Overall MAE
    total_mae = sum(g["abs_error"] for g in games) / len(games)
    total_bias = sum(g["error"] for g in games) / len(games)
    
    print(f"\n  Overall: {len(games)} graded games")
    print(f"  MAE (Mean Absolute Error): {total_mae:.1f} points")
    print(f"  Bias (mean signed error):  {total_bias:+.1f} points")
    
    # By league
    league_stats = {}
    for g in games:
        lid = g.get("league_id", "?")
        lname = g.get("league", "?")
        key = f"{lid}:{lname}"
        if key not in league_stats:
            league_stats[key] = {"name": lname, "errors": [], "abs_errors": []}
        league_stats[key]["errors"].append(g["error"])
        league_stats[key]["abs_errors"].append(g["abs_error"])
    
    print(f"\n  {'League':<30} {'N':>4} {'MAE':>6} {'Bias':>7}")
    print("  " + "-" * 50)
    
    rows = []
    for key, stats in league_stats.items():
        n = len(stats["abs_errors"])
        mae = sum(stats["abs_errors"]) / n
        bias = sum(stats["errors"]) / n
        rows.append((stats["name"], n, mae, bias))
    
    rows.sort(key=lambda x: x[2])  # Sort by MAE ascending
    for name, n, mae, bias in rows:
        print(f"  {name:<30} {n:>4} {mae:>6.1f} {bias:>+7.1f}")
    
    # Top 5 worst predictions
    games.sort(key=lambda x: x["abs_error"], reverse=True)
    print(f"\n  Top 5 Worst Predictions:")
    for g in games[:5]:
        print(f"    |{g['abs_error']:>5.1f}| {g['away']} @ {g['home']} "
              f"(model:{g['model_total']:.1f} actual:{g['actual_total']:.0f})")
    
    # Over/Under accuracy
    correct_ou = 0
    total_ou = 0
    for g in games:
        if g.get("model_total") and g.get("actual_total"):
            total_ou += 1
            # Check if model was on the right side of the actual
            # (This is directional accuracy relative to actual, not market)
    
    print(f"\n{'=' * 70}\n")


if __name__ == "__main__":
    main()
