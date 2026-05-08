import json
import os
import glob
import sys
import numpy as np

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

DATA_DIR = "data/basketball"
TRACKING_EPOCH = "2026-03-25"

def analyze_volatility():
    all_files = sorted(glob.glob(os.path.join(DATA_DIR, "universal_predictions_*.json")))
    files = [f for f in all_files if os.path.basename(f).replace("universal_predictions_", "").replace(".json", "") >= TRACKING_EPOCH]
    
    print(f"\n  Running Volatility-Only Audit (Data-Leakage Free)...")
    
    # band -> list of (abs_delta, signed_delta, actual_total)
    performance = {
        "[TIER 1] (Extremely Stable, <14.8)": [],
        "[TIER 2] (Solid, 14.8 - 16.6)": [],
        "[TIER 3] (Mixed Volatility)": [],
        "[TIER 4] (Wildcards, >16.6)": []
    }
    
    total_graded = 0
    
    for f_path in files:
        try:
            with open(f_path, encoding="utf-8") as f:
                data = json.load(f)
            preds = data.get("predictions", [])
            for p in preds:
                h_s = p.get("actual_home_score")
                a_s = p.get("actual_away_score")
                model_total = p.get("model_total")
                
                if h_s is not None and a_s is not None and model_total:
                    if p.get("status") == "AOT":
                        continue
                    
                    # USE STRICTLY HISTORICAL SNAPSHOTTED VOLATILITY
                    vol_h = p.get("home_team_volatility")
                    vol_a = p.get("away_team_volatility")
                    
                    if vol_h is None or vol_a is None:
                        continue
                    
                    if vol_h < 14.8 and vol_a < 14.8:
                        band = "[TIER 1] (Extremely Stable, <14.8)"
                    elif vol_h <= 16.6 and vol_a <= 16.6:
                        band = "[TIER 2] (Solid, 14.8 - 16.6)"
                    elif vol_h > 16.6 and vol_a > 16.6:
                        band = "[TIER 4] (Wildcards, >16.6)"
                    else:
                        band = "[TIER 3] (Mixed Volatility)"
                    
                    actual_total = h_s + a_s
                    delta = abs(actual_total - model_total)
                    signed_delta = actual_total - model_total
                    
                    performance[band].append((delta, signed_delta, actual_total))
                    total_graded += 1
        except Exception as e:
            continue

    print(f"\nPURE VOLATILITY TIER AUDIT (Epoch: {TRACKING_EPOCH}+)")
    print(f"Total Graded Games: {total_graded}")
    print("=" * 105)
    print(f"{'Tier':<40} | {'Games':>5} | {'MAE':>6} | {'Bias':>6} | {'Floor Coverage (-10)':>20}")
    print("-" * 105)
    
    for band in performance.keys():
        results = performance[band]
        if not results:
            print(f"{band:<40} | {0:>5} | {'N/A':>6} | {'N/A':>6} | {'N/A':>20}")
            continue
            
        deltas = [r[0] for r in results]
        signed = [r[1] for r in results]
        
        mae = np.mean(deltas)
        bias = np.mean(signed)
        
        wins_10 = sum(1 for r in results if r[1] >= -10)
        win_rate = (wins_10 / len(results)) * 100
        
        print(f"{band:<40} | {len(results):>5} | {mae:>6.2f} | {bias:>+6.2f} | {wins_10:>7}/{len(results):<4} ({win_rate:.1f}%)")
    
    print("=" * 105)

if __name__ == "__main__":
    analyze_volatility()
