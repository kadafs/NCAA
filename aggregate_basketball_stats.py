import json
import os
import glob
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "basketball")
OUTPUT_FILE = os.path.join(DATA_DIR, "league_leaderboard.json")

def process_file(file_path, stats_dict):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        predictions = data.get("predictions", [])
        
        for p in predictions:
            # Only process graded predictions
            if p.get("actual_result") is None:
                continue
                
            league_name = p.get("league", "Unknown").upper()
            decision = p.get("decision", "")
            
            # Outcome grade (1X2 / ML)
            pred_1x2 = p.get("predicted_result")
            actual_1x2 = p.get("actual_result")
            is_1x2_win = (pred_1x2 == actual_1x2)
            
            # Totals grade (The Delta Matrix)
            tier = p.get("accuracy_tier")
            rpe = p.get("total_rpe")
            
            if league_name not in stats_dict:
                stats_dict[league_name] = {
                    "1x2_w": 0, "1x2_l": 0,
                    "bullseyes": 0, "excellents": 0, "solids": 0,
                    "misses": 0, "busts": 0, "ots": 0,
                    "sum_rpe": 0.0, "count_rpe": 0
                }
                
            l_stats = stats_dict[league_name]
            
            # Tally 1X2 / Moneyline
            if pred_1x2 and actual_1x2:
                if is_1x2_win:
                    l_stats["1x2_w"] += 1
                else:
                    l_stats["1x2_l"] += 1
            
            # Tally Totals Accuracy Matrix
            if tier == "🎯 BULLSEYE": l_stats["bullseyes"] += 1
            elif tier == "🟢 EXCELLENT": l_stats["excellents"] += 1
            elif tier == "🟡 SOLID": l_stats["solids"] += 1
            elif tier == "🟠 MISS": l_stats["misses"] += 1
            elif tier == "🔴 BUST": l_stats["busts"] += 1
            elif tier == "🚨 OT WARP": l_stats["ots"] += 1
            
            if rpe is not None:
                l_stats["sum_rpe"] += rpe
                l_stats["count_rpe"] += 1
                    
    except Exception as e:
        print(f"Error processing {os.path.basename(file_path)}: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Aggregate historical basketball performance stats.")
    parser.add_argument("--date", help="End date (YYYY-MM-DD) for aggregation. Only files on or before this date are included.")
    parser.add_argument("--verbose", action="store_true", help="Print names of processed files")
    args = parser.parse_args()

    print("Aggregating historical basketball league performance...")
    search_pattern = os.path.join(DATA_DIR, "universal_predictions_*.json")
    all_files = glob.glob(search_pattern)
    
    # Filter files by date if requested
    files = []
    if args.date:
        try:
            target_dt = datetime.strptime(args.date, "%Y-%m-%d")
            for f in all_files:
                file_date_str = os.path.basename(f).replace("universal_predictions_", "").replace(".json", "")
                try:
                    file_dt = datetime.strptime(file_date_str, "%Y-%m-%d")
                    if file_dt <= target_dt:
                        files.append(f)
                except ValueError:
                    continue
        except ValueError:
            print(f"Invalid date format: {args.date}. Using all files.")
            files = all_files
    else:
        files = all_files

    league_stats = {}
    
    for f in sorted(files):
        if args.verbose:
            print(f" - Processing {os.path.basename(f)}...")
        process_file(f, league_stats)
        
    # Compile into array and calculate metrics
    leaderboard = []
    
    for lname, s in league_stats.items():
        count_rpe = s["count_rpe"]
        mape = (s["sum_rpe"] / count_rpe) if count_rpe > 0 else 0.0
        
        x_w = s["1x2_w"]
        x_l = s["1x2_l"]
        x_total = x_w + x_l
        x_hit_rate = (x_w / x_total * 100) if x_total > 0 else 0.0
            
        leaderboard.append({
            "name": lname,
            "mape": round(mape, 2),
            "graded_totals": count_rpe,
            "bullseyes": s["bullseyes"],
            "excellents": s["excellents"],
            "solids": s["solids"],
            "misses": s["misses"],
            "busts": s["busts"],
            "ots": s["ots"],
            "outcome_w": x_w,
            "outcome_l": x_l,
            "outcome_hit_rate": round(x_hit_rate, 1)
        })
        
    # Sort by MAPE ascending (lowest error is best, ignoring 0 mapes)
    leaderboard.sort(key=lambda x: (x["mape"] == 0, x["mape"]))
    
    output_data = {
        "updated_at": datetime.now().isoformat(),
        "total_leagues": len(leaderboard),
        "leaderboard": leaderboard
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully aggregated {len(files)} files into league_leaderboard.json.")
    if args.date:
        print(f"Filter: Files on or before {args.date}")
    print(f"Tracked {len(leaderboard)} unique leagues.")

if __name__ == "__main__":
    main()
