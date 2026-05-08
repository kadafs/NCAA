import json
import csv
import glob
import os
import numpy as np

def audit_csvs():
    csv_files = [
        r"C:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\data\confidence_reports\confidence_2026-05-05_graded4.csv",
        r"C:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\data\confidence_reports\confidence_2026-05-06_graded4.csv",
        r"C:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\data\confidence_reports\confidence_2026-05-07.csv"
    ]
    
    json_dir = r"C:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\data\basketball"
    
    actuals = {}
    json_files = glob.glob(os.path.join(json_dir, "universal_predictions_*.json"))
    for jf in json_files:
        try:
            with open(jf, encoding="utf-8") as f:
                data = json.load(f)
            preds = data.get("predictions", [])
            for p in preds:
                date = p.get("date")
                away = p.get("away_team", "").strip()
                home = p.get("home_team", "").strip()
                hs = p.get("actual_home_score")
                as_ = p.get("actual_away_score")
                stage = p.get("stage", "")
                if hs is not None and as_ is not None and p.get("status") != "AOT":
                    actuals[(date, away, home)] = {
                        "total": hs + as_,
                        "stage": stage
                    }
        except:
            continue

    performance = {
        "[ELITE]": [],
        "[HIGH]": [],
        "[SOLID]": [],
        "[MODERATE]": [],
        "[LOW]": [],
        "[AVOID]": []
    }
    
    total_graded = 0
    missing_scores = 0

    print("--- MISSING GAMES LOG ---")
    for csv_file in csv_files:
        if not os.path.exists(csv_file):
            continue
            
        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row.get("date")
                away = row.get("away_team", "").strip()
                home = row.get("home_team", "").strip()
                band = row.get("band", "").strip()
                model_total_str = row.get("model_total")
                bias_adj_str = row.get("bias_adjusted_total")
                
                if not model_total_str or not bias_adj_str or band not in performance:
                    continue
                    
                model_total = float(model_total_str)
                bias_adjusted_total = float(bias_adj_str)
                
                actual_data = actuals.get((date, away, home))
                
                if actual_data is not None:
                    stage = actual_data.get("stage", "").lower()
                    
                    # PLAYOFF FILTER
                    if "playoff" in stage or "final" in stage or "quarter" in stage or "semi" in stage:
                        continue
                        
                    actual_total = actual_data.get("total")
                    
                    # GRADE AGAINST BIAS_ADJUSTED_TOTAL INSTEAD OF RAW MODEL TOTAL
                    delta = abs(actual_total - bias_adjusted_total)
                    signed_delta = actual_total - bias_adjusted_total
                    performance[band].append((delta, signed_delta, actual_total))
                    total_graded += 1
                else:
                    missing_scores += 1
                    # print(f"Missing: {date} | {away} @ {home}")

    print("-------------------------\n")
    print(f"CSV SNAPSHOT AUDIT (May 5th - May 7th)")
    print(f"Grouped by FULL CONFIDENCE TIER ('band' in CSV), graded against Bias-Adjusted Total")
    print(f"** EXCLUDING PLAYOFFS/FINALS **")
    print(f"Total Graded Games (Regular Season Only): {total_graded}")
    print("=" * 115)
    print(f"{'Tier':<12} | {'Games':>5} | {'MAE':>6} | {'Bias':>6} | {'Flat Floor':>16} | {'-5 Floor':>16} | {'-10 Floor':>16}")
    print("-" * 115)
    
    for band in ["[ELITE]", "[HIGH]", "[SOLID]", "[MODERATE]", "[LOW]", "[AVOID]"]:
        results = performance[band]
        if not results:
            print(f"{band:<12} | {0:>5} | {'N/A':>6} | {'N/A':>6} | {'N/A':>20}")
            continue
            
        deltas = [r[0] for r in results]
        signed = [r[1] for r in results]
        
        mae = np.mean(deltas)
        bias = np.mean(signed)
        
        wins_0 = sum(1 for r in results if r[1] >= 0)
        wins_5 = sum(1 for r in results if r[1] >= -5)
        wins_10 = sum(1 for r in results if r[1] >= -10)
        
        win_rate_0 = (wins_0 / len(results)) * 100
        win_rate_5 = (wins_5 / len(results)) * 100
        win_rate_10 = (wins_10 / len(results)) * 100
        
        s_0 = f"{wins_0}/{len(results)} ({win_rate_0:.0f}%)"
        s_5 = f"{wins_5}/{len(results)} ({win_rate_5:.0f}%)"
        s_10 = f"{wins_10}/{len(results)} ({win_rate_10:.0f}%)"
        
        print(f"{band:<12} | {len(results):>5} | {mae:>6.2f} | {bias:>+6.2f} | {s_0:>16} | {s_5:>16} | {s_10:>16}")
    
    print("=" * 115)

if __name__ == "__main__":
    audit_csvs()
