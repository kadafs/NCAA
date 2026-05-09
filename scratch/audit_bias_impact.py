import json
import os
import csv
import glob
from datetime import datetime
import numpy as np

# Path Configuration
CONFIDENCE_DIR = r"c:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\data\confidence_reports"
PREDICTIONS_DIR = r"c:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\data\basketball"

# Audit window
DATES = ["2026-05-05", "2026-05-06", "2026-05-07"]

# Bias Bins
def get_bias_bin(bias):
    if bias > 5.0:   return "Heavy Positive (> +5)"
    if bias > 1.0:   return "Slight Positive (+1 to +5)"
    if bias >= -1.0: return "Neutral (-1 to +1)"
    if bias >= -5.0: return "Slight Negative (-5 to -1)"
    return "Heavy Negative (< -5)"

BIAS_ORDER = [
    "Heavy Positive (> +5)",
    "Slight Positive (+1 to +5)",
    "Neutral (-1 to +1)",
    "Slight Negative (-5 to -1)",
    "Heavy Negative (< -5)"
]

def load_predictions(date_str):
    path = os.path.join(PREDICTIONS_DIR, f"universal_predictions_{date_str}.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
        indexed = {}
        for p in data.get("predictions", []):
            key = (p.get("home_team"), p.get("away_team"))
            indexed[key] = p
        return indexed

def audit_low_tier_bias():
    print(f"\n{'='*100}")
    print(f"  AUDIT: BIAS IMPACT WITHIN [LOW] CONFIDENCE TIER")
    print(f"  Target: Games categorized as [LOW] (Underpriced / Low Stability)")
    print(f"{'='*100}")

    # Groups: Positive vs Negative Bias
    # { "games": 0, "hits": 0, "errors": [] }
    stats = {
        "Positive Bias (> 0)": {"games": 0, "hits": 0, "errors": []},
        "Negative Bias (<= 0)": {"games": 0, "hits": 0, "errors": []}
    }

    for date in DATES:
        possible_patterns = [f"confidence_{date}.csv", f"confidence_{date}_graded4.csv", f"confidence_{date}_graded3.csv"]
        target_file = next((os.path.join(CONFIDENCE_DIR, p) for p in possible_patterns if os.path.exists(os.path.join(CONFIDENCE_DIR, p))), None)
        if not target_file: continue
        preds = load_predictions(date)
        
        with open(target_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["band"] != "[LOW]": continue
                
                home, away = row["home_team"], row["away_team"]
                model_total = float(row["model_total"])
                game_bias = float(row.get("avg_bias", 0))
                
                p = preds.get((home, away))
                if not p: continue
                
                # Skip Playoffs
                stage = p.get("stage", "").lower()
                if any(k in stage for k in ["final", "semi", "quarter", "playoff"]): continue
                
                h_s, a_s = p.get("actual_home_score"), p.get("actual_away_score")
                if h_s is None or a_s is None: continue
                
                actual_total = h_s + a_s
                error = actual_total - model_total
                
                group = "Positive Bias (> 0)" if game_bias > 0 else "Negative Bias (<= 0)"
                stats[group]["games"] += 1
                stats[group]["errors"].append(error)
                if actual_total >= (model_total - 10):
                    stats[group]["hits"] += 1

    # Print Report
    print(f"{'Bias Group':<25} | {'Games':>5} | {'Avg Error':>12} | {'Hit Rate (-10 Rule)':>22}")
    print("-" * 100)
    for g in ["Positive Bias (> 0)", "Negative Bias (<= 0)"]:
        s = stats[g]
        if s["games"] == 0: continue
        avg_err = sum(s["errors"]) / s["games"]
        rate = (s["hits"] / s["games"]) * 100
        print(f"{g:<25} | {s['games']:>5} | {avg_err:>+12.2f} | {s['hits']:>8}/{s['games']:<4} ({rate:>6.1f}%)")
    
    print("-" * 100)
    print(f"Total [LOW] Tier Games: {sum(s['games'] for s in stats.values())}")
    print(f"{'='*100}\n")

if __name__ == "__main__":
    audit_low_tier_bias()
