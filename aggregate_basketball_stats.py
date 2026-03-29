import json
import os
import glob
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "basketball")
OUTPUT_FILE = os.path.join(DATA_DIR, "league_leaderboard.json")
TEAM_OUTPUT_FILE = os.path.join(DATA_DIR, "basketball_leaderboard.json")

# ==========================================
# TRACKING EPOCH RESET
# Define the date when the "V2" mathematical engine launched.
# The dashboard leaderboard will ONLY aggregate predictions from this date forward.
# This prevents corrupted legacy baselines from polluting the current MAPE tracking.
# ==========================================
TRACKING_EPOCH = "2026-03-25"

def _blank_model_stats():
    return {
        "1x2_w": 0, "1x2_l": 0,
        "bullseyes": 0, "excellents": 0, "solids": 0,
        "misses": 0, "busts": 0, "ots": 0,
        "sum_rpe": 0.0, "count_rpe": 0,
        "sum_delta": 0.0, "count_delta": 0,
        "sum_signed_delta": 0.0, "count_signed_delta": 0,
        "signed_deltas": []
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
    # total_delta tracking (for MAE) goes here in process_file
    if signed_delta is not None:
        bucket["sum_signed_delta"]   += signed_delta
        bucket["count_signed_delta"] += 1
        bucket["signed_deltas"].append(signed_delta)

def process_file(file_path, stats_dict, team_stats_dict):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        predictions = data.get("predictions", [])

        for p in predictions:
            if p.get("actual_result") is None:
                continue

            league_id    = p.get("league_id")
            league_name  = p.get("league", "Unknown")
            country      = p.get("country", "")
            
            # Key by league_id if available, fallback to unique composite string
            key = str(league_id) if league_id else f"{country}_{league_name}".upper()
            display_name = f"{country.upper()} — {league_name.upper()}" if country else league_name.upper()

            model_arch   = p.get("model_architecture", "[  SRS   ]")
            is_adv       = "ADVANCED" in (model_arch or "")
            model_key    = "adv" if is_adv else "srs"

            pred_1x2     = p.get("predicted_result")
            actual_1x2   = p.get("actual_result")
            tier         = p.get("accuracy_tier")
            rpe          = p.get("total_rpe")
            signed_delta = p.get("signed_delta")

            # Create team keys
            home_team = p.get("home_team", "Unknown")
            away_team = p.get("away_team", "Unknown")

            if key not in stats_dict:
                stats_dict[key] = {
                    "league_id": league_id,
                    "name": display_name,
                    "srs": _blank_model_stats(),
                    "adv": _blank_model_stats()
                }

            for t_name in [home_team, away_team]:
                if t_name not in team_stats_dict:
                    team_stats_dict[t_name] = {
                        "name": t_name,
                        "league_id": league_id,
                        "league_name": display_name,
                        "srs": _blank_model_stats(),
                        "adv": _blank_model_stats()
                    }
                
            # MAE Tracking
            total_delta = p.get("total_delta")
            if total_delta is not None and tier != "🚨 OT WARP":
                stats_dict[key][model_key]["sum_delta"] += total_delta
                stats_dict[key][model_key]["count_delta"] += 1
                for t_name in [home_team, away_team]:
                    team_stats_dict[t_name][model_key]["sum_delta"] += total_delta
                    team_stats_dict[t_name][model_key]["count_delta"] += 1

            _tally(stats_dict[key][model_key],
                   pred_1x2, actual_1x2, tier, rpe, signed_delta)
                   
            for t_name in [home_team, away_team]:
                _tally(team_stats_dict[t_name][model_key],
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
    
    # Filter files by Tracking Epoch and explicit user flags
    files = []
    
    start_dt = datetime.strptime(TRACKING_EPOCH, "%Y-%m-%d")
    end_dt   = datetime.strptime(args.date, "%Y-%m-%d") if args.date else None
    
    for f in all_files:
        file_date_str = os.path.basename(f).replace("universal_predictions_", "").replace(".json", "")
        try:
            file_dt = datetime.strptime(file_date_str, "%Y-%m-%d")
            
            # 1. Enforce Tracking Epoch (V2 Engine Reset)
            if file_dt < start_dt:
                continue
                
            # 2. Enforce explicit end date if passed
            if end_dt and file_dt > end_dt:
                continue
                
            files.append(f)
        except ValueError:
            continue
            
    if not files:
        print(f"No prediction files found valid for the tracking epoch (>= {TRACKING_EPOCH}).")

    league_stats = {}
    team_stats = {}
    
    for f in sorted(files):
        if args.verbose:
            print(f" - Processing {os.path.basename(f)}...")
        process_file(f, league_stats, team_stats)
        
    # Compile into array and calculate metrics
    leaderboard = []

    import math
    def _compile_model(s):
        """Turn a raw stats bucket into display-ready metrics."""
        count_rpe    = s["count_rpe"]
        count_signed = s["count_signed_delta"]
        count_delta  = s.get("count_delta", 0)
        x_w, x_l    = s["1x2_w"], s["1x2_l"]
        x_total      = x_w + x_l
        
        # Calculate Volatility (Standard Deviation)
        volatility = None
        if count_signed > 1:
            mean = s["sum_signed_delta"] / count_signed
            variance = sum((x - mean) ** 2 for x in s["signed_deltas"]) / (count_signed - 1)
            volatility = round(math.sqrt(variance), 2)
        elif count_signed == 1:
            volatility = 0.0

        return {
            "mape":              round(s["sum_rpe"] / count_rpe, 2) if count_rpe else 0.0,
            "mae":               round(s.get("sum_delta", 0) / count_delta, 2) if count_delta else None,
            "volatility_index":  volatility,
            "graded_totals":     count_delta if count_delta > 0 else count_rpe,
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

    for key, models in league_stats.items():
        srs = _compile_model(models["srs"])
        adv = _compile_model(models["adv"])
        has_adv = adv["graded_totals"] > 0

        # ADV is primary when available; fall back to SRS
        primary = adv if has_adv else srs

        entry = {
            "name": models["name"],
            "league_id": models["league_id"],
            "mape":               primary["mape"],
            "mae":                primary["mae"],
            "graded_totals":      primary["graded_totals"],
            "bullseyes":          primary["bullseyes"],
            "excellents":         primary["excellents"],
            "solids":             primary["solids"],
            "misses":             primary["misses"],
            "busts":              primary["busts"],
            "ots":                primary["ots"],
            "avg_signed_delta":   primary["avg_signed_delta"],
            "volatility_index":   primary["volatility_index"],
            "outcome_w":          primary["outcome_w"],
            "outcome_l":          primary["outcome_l"],
            "outcome_hit_rate":   primary["outcome_hit_rate"],
            "srs":  srs if srs["graded_totals"] > 0 else None,
            "adv":  adv if has_adv else None,
        }
        leaderboard.append(entry)

    leaderboard.sort(key=lambda x: (x["mape"] == 0, x["mape"]))
    output_data = {
        "updated_at": datetime.now().isoformat(),
        "total_leagues": len(leaderboard),
        "leaderboard": leaderboard
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    # Build Team Leaderboard exactly the same way
    team_leaderboard = []
    for key, models in team_stats.items():
        srs = _compile_model(models["srs"])
        adv = _compile_model(models["adv"])
        has_adv = adv["graded_totals"] > 0
        primary = adv if has_adv else srs

        entry = {
            "name": models["name"],
            "league": models.get("league_name"),
            "league_id": models.get("league_id"),
            "mape":               primary["mape"],
            "mae":                primary["mae"],
            "graded_totals":      primary["graded_totals"],
            "bullseyes":          primary["bullseyes"],
            "excellents":         primary["excellents"],
            "solids":             primary["solids"],
            "misses":             primary["misses"],
            "busts":              primary["busts"],
            "avg_signed_delta":   primary["avg_signed_delta"],
            "volatility_index":   primary["volatility_index"],
            "outcome_w":          primary["outcome_w"],
            "outcome_l":          primary["outcome_l"],
            "outcome_hit_rate":   primary["outcome_hit_rate"],
            "srs":  srs if srs["graded_totals"] > 0 else None,
            "adv":  adv if has_adv else None,
        }
        team_leaderboard.append(entry)

    # Sort teams by highest outcome_hit_rate first, then lowest MAE
    team_leaderboard.sort(key=lambda x: (-x["outcome_hit_rate"], x["mae"] or 999))
    team_output_data = {
        "updated_at": datetime.now().isoformat(),
        "total_teams": len(team_leaderboard),
        "leaderboard": team_leaderboard
    }
    with open(TEAM_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(team_output_data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully aggregated {len(files)} files.")
    print(f"Tracked {len(leaderboard)} leagues into league_leaderboard.json.")
    print(f"Tracked {len(team_leaderboard)} teams into basketball_leaderboard.json.")

if __name__ == "__main__":
    main()
