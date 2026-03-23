import json
import os
import glob
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "basketball")
OUTPUT_FILE = os.path.join(DATA_DIR, "league_leaderboard.json")

def _blank_model_stats():
    return {
        "1x2_w": 0, "1x2_l": 0,
        "bullseyes": 0, "excellents": 0, "solids": 0,
        "misses": 0, "busts": 0, "ots": 0,
        "sum_rpe": 0.0, "count_rpe": 0,
        "sum_signed_delta": 0.0, "count_signed_delta": 0
    }

def _tally(bucket, pred_1x2, actual_1x2, tier, rpe, signed_delta):
    """Add one prediction's data into a stats bucket."""
    if pred_1x2 and actual_1x2:
        if pred_1x2 == actual_1x2:
            bucket["1x2_w"] += 1
        else:
            bucket["1x2_l"] += 1
    if tier == "🎯 BULLSEYE":    bucket["bullseyes"]  += 1
    elif tier == "🟢 EXCELLENT": bucket["excellents"] += 1
    elif tier == "🟡 SOLID":    bucket["solids"]     += 1
    elif tier == "🟠 MISS":     bucket["misses"]     += 1
    elif tier == "🔴 BUST":     bucket["busts"]      += 1
    elif tier == "🚨 OT WARP":  bucket["ots"]        += 1
    if rpe is not None:
        bucket["sum_rpe"]    += rpe
        bucket["count_rpe"]  += 1
    if signed_delta is not None:
        bucket["sum_signed_delta"]   += signed_delta
        bucket["count_signed_delta"] += 1

def process_file(file_path, stats_dict):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        predictions = data.get("predictions", [])

        for p in predictions:
            if p.get("actual_result") is None:
                continue

            league_name  = p.get("league", "Unknown").upper()
            model_arch   = p.get("model_architecture", "[  SRS   ]")
            is_adv       = "ADVANCED" in (model_arch or "")
            model_key    = "adv" if is_adv else "srs"

            pred_1x2     = p.get("predicted_result")
            actual_1x2   = p.get("actual_result")
            tier         = p.get("accuracy_tier")
            rpe          = p.get("total_rpe")
            signed_delta = p.get("signed_delta")

            if league_name not in stats_dict:
                stats_dict[league_name] = {"srs": _blank_model_stats(), "adv": _blank_model_stats()}

            _tally(stats_dict[league_name][model_key],
                   pred_1x2, actual_1x2, tier, rpe, signed_delta)

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

    def _compile_model(s):
        """Turn a raw stats bucket into display-ready metrics."""
        count_rpe    = s["count_rpe"]
        count_signed = s["count_signed_delta"]
        x_w, x_l    = s["1x2_w"], s["1x2_l"]
        x_total      = x_w + x_l
        return {
            "mape":              round(s["sum_rpe"] / count_rpe, 2) if count_rpe else 0.0,
            "graded_totals":     count_rpe,
            "bullseyes":         s["bullseyes"],
            "excellents":        s["excellents"],
            "solids":            s["solids"],
            "misses":            s["misses"],
            "busts":             s["busts"],
            "ots":               s["ots"],
            "avg_signed_delta":  round(s["sum_signed_delta"] / count_signed, 2) if count_signed else None,
            "outcome_w":         x_w,
            "outcome_l":         x_l,
            "outcome_hit_rate":  round(x_w / x_total * 100, 1) if x_total else 0.0,
        }

    for lname, models in league_stats.items():
        srs = _compile_model(models["srs"])
        adv = _compile_model(models["adv"])
        has_adv = adv["graded_totals"] > 0

        entry = {
            "name": lname,
            # Combined (SRS) stats — primary sort key, backwards-compatible
            "mape":               srs["mape"],
            "graded_totals":      srs["graded_totals"],
            "bullseyes":          srs["bullseyes"],
            "excellents":         srs["excellents"],
            "solids":             srs["solids"],
            "misses":             srs["misses"],
            "busts":              srs["busts"],
            "ots":                srs["ots"],
            "avg_signed_delta":   srs["avg_signed_delta"],
            "outcome_w":          srs["outcome_w"],
            "outcome_l":          srs["outcome_l"],
            "outcome_hit_rate":   srs["outcome_hit_rate"],
            # Per-model breakdowns
            "srs":  srs,
            "adv":  adv if has_adv else None,
        }
        leaderboard.append(entry)
        
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
