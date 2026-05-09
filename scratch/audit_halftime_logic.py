import json
import os
import csv
import glob
from datetime import datetime

# Path Configuration
CONFIDENCE_DIR = r"c:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\data\confidence_reports"
PREDICTIONS_DIR = r"c:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\data\basketball"

# Audit window
DATES = ["2026-05-05", "2026-05-06", "2026-05-07"]

# Confidence Bands in order
BANDS = ["[ELITE]", "[HIGH]", "[SOLID]", "[MODERATE]", "[LOW]", "[AVOID]"]

def load_predictions(date_str):
    path = os.path.join(PREDICTIONS_DIR, f"universal_predictions_{date_str}.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
        # Index by (home, away) for easy lookup
        indexed = {}
        for p in data.get("predictions", []):
            key = (p.get("home_team"), p.get("away_team"))
            indexed[key] = p
        return indexed

def audit_halftime():
    print(f"\n{'='*100}")
    print(f"  HALF-TIME CONFIDENCE AUDIT (May 5 - May 7)")
    print(f"  Target: Halftime Total >= (Bias-Adjusted Total / 2)")
    print(f"{'='*100}")

    # band -> { "total": 0, "ht_hit": 0, "ht_minus_5_hit": 0, "final_hit_minus_10": 0, "biases": [], "maes": [] }
    stats = {b: {"total": 0, "ht_hit": 0, "ht_minus_5_hit": 0, "final_hit_minus_10": 0, "biases": [], "maes": []} for b in BANDS}

    for date in DATES:
        # Use the most complete file available for each date
        possible_patterns = [
            f"confidence_{date}.csv",
            f"confidence_{date}_graded3.csv",
            f"confidence_{date}_graded4.csv"
        ]
        
        target_file = None
        for p in possible_patterns:
            fpath = os.path.join(CONFIDENCE_DIR, p)
            if os.path.exists(fpath):
                target_file = fpath
                break
        
        if not target_file:
            print(f"  [WARN] No suitable CSV found for {date}")
            continue
        
        print(f"  Auditing {os.path.basename(target_file)}...")
        preds = load_predictions(date)
        
        with open(target_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                band = row["band"].strip()
                if band not in stats:
                    continue
                
                home = row["home_team"]
                away = row["away_team"]
                adj_total = float(row["bias_adjusted_total"])
                
                # Find in JSON
                p = preds.get((home, away))
                if not p:
                    continue
                
                # Skip Playoffs
                stage = p.get("stage", "").lower()
                if any(k in stage for k in ["final", "semi", "quarter", "playoff", "3rd place"]):
                    continue
                
                h_s = p.get("actual_home_score")
                a_s = p.get("actual_away_score")
                ht_total = p.get("halftime_total")
                
                if h_s is None or a_s is None:
                    continue
                
                actual_total = h_s + a_s
                signed_error = actual_total - adj_total
                abs_error = abs(actual_total - adj_total)
                
                stats[band]["total"] += 1
                stats[band]["biases"].append(signed_error)
                stats[band]["maes"].append(abs_error)
                
                # Half-Time Evaluation
                if ht_total is not None:
                    if ht_total >= (adj_total / 2):
                        stats[band]["ht_hit"] += 1
                    if ht_total >= (adj_total / 2) - 5:
                        stats[band]["ht_minus_5_hit"] += 1
                
                # Final Evaluation (The -10 rule)
                if actual_total >= (adj_total - 10):
                    stats[band]["final_hit_minus_10"] += 1

    # Print Report
    print(f"{'Band':<12} | {'Games':>5} | {'Avg Bias':>10} | {'Avg MAE':>10} | {'HT Hit (50%)':>15} | {'Final Hit (-10)':>15}")
    print("-" * 115)
    
    total_games = 0
    for b in BANDS:
        s = stats[b]
        if s["total"] == 0:
            continue
        
        total_games += s["total"]
        avg_bias = sum(s["biases"]) / s["total"]
        avg_mae = sum(s["maes"]) / s["total"]
        ht_rate = (s["ht_hit"] / s["total"]) * 100
        final_rate = (s["final_hit_minus_10"] / s["total"]) * 100
        
        print(f"{b:<12} | {s['total']:>5} | {avg_bias:>+10.2f} | {avg_mae:>10.2f} | {s['ht_hit']:>4}/{s['total']:<3} ({ht_rate:>5.1f}%) | {s['final_hit_minus_10']:>4}/{s['total']:<3} ({final_rate:>5.1f}%)")
    
    print("-" * 115)
    print(f"Total Regular Season Games Audited: {total_games}")
    print(f"{'='*100}\n")

if __name__ == "__main__":
    audit_halftime()
