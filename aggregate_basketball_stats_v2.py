import json
import os
import glob
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from utils.epoch_config import get_earliest_epoch, is_game_valid

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "basketball")
OUTPUT_FILE = os.path.join(DATA_DIR, "league_leaderboard_v2.json")
TEAM_OUTPUT_FILE = os.path.join(DATA_DIR, "basketball_leaderboard_v2.json")

# ==========================================
# TRACKING EPOCH RESET
# Epoch configuration is centralised in configs/tracking_epochs.json.
# Use get_earliest_epoch() for file-level filtering and is_game_valid()
# inside prediction loops for per-league epoch enforcement.
# To add a league-specific epoch override, edit that JSON file.
# ==========================================

# ==========================================
# LEAGUE ID MERGES (MIGRATIONS)
# Mapping historical/alternative league IDs to a single canonical ID
# to preserve grading history across API name/ID changes.
# ==========================================
LEAGUE_ID_MERGES = {
    368: [374, 65],  # BNXT League -> Pro Basketball League (Belgium) AND DBL (Netherlands)
    24:  [374],       # Euromillions -> Pro Basketball League (Belgium)
}

# ==========================================
# SRS TO ADVANCED PROMOTION
# Force historical SRS data to be attributed to the ADV bucket
# for leagues that have fully migrated to the efficiency engine.
# This ensures the [ADV] badge appears on the dashboard immediately.
# ==========================================
PROMOTE_SRS_TO_ADV = {
    13,  # USA - WNBA
    207, 208, 209, 210, 211, 212, 213, 214, 215, 216 # Australia - NBL1
}

def _blank_model_stats():
    return {
        "1x2_w": 0, "1x2_l": 0,
        "bullseyes": 0, "excellents": 0, "solids": 0,
        "misses": 0, "busts": 0, "ots": 0,
        "sum_rpe": 0.0, "count_rpe": 0,
        "sum_delta": 0.0, "count_delta": 0,
        "sum_signed_delta": 0.0, "count_signed_delta": 0,
        "signed_deltas": [],
        # Halftime tracking
        "ht_count": 0, "ht_pct_sum": 0.0, "ht_on_pace": 0,
        # Hit Rate tracking (-5 pt buffer floor)
        "flat_floor_hits": 0, "flat_floor_total": 0,
    }

def _tally(bucket, pred_1x2, actual_1x2, tier, rpe, signed_delta):
    """Add one prediction's data into a stats bucket."""
    if pred_1x2 and actual_1x2:
        if pred_1x2 == actual_1x2:
            bucket["1x2_w"] += 1
        else:
            bucket["1x2_l"] += 1
    # Support both legacy emoji strings and new ASCII strings (backward compat)
    if tier in ("BULLSEYE", "\U0001f3af BULLSEYE"):    bucket["bullseyes"]  += 1
    elif tier in ("EXCELLENT", "\U0001f7e2 EXCELLENT"): bucket["excellents"] += 1
    elif tier in ("SOLID", "\U0001f7e1 SOLID"):         bucket["solids"]     += 1
    elif tier in ("MISS", "\U0001f7e0 MISS"):          bucket["misses"]     += 1
    elif tier in ("BUST", "\U0001f534 BUST"):          bucket["busts"]      += 1
    elif tier in ("OT WARP", "\U0001f6a8 OT WARP"):   bucket["ots"]        += 1
    if rpe is not None:
        bucket["sum_rpe"]    += rpe
        bucket["count_rpe"]  += 1
    if signed_delta is not None:
        bucket["sum_signed_delta"]   += signed_delta
        bucket["count_signed_delta"] += 1
        bucket["signed_deltas"].append(signed_delta)

def process_file(file_path, file_date_str, stats_dict, team_stats_dict):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        predictions = data.get("predictions", [])

        for p in predictions:
            if p.get("actual_result") is None:
                continue

            orig_id = p.get("league_id")
            target_ids = LEAGUE_ID_MERGES.get(orig_id, [orig_id])
            
            for league_id in target_ids:
                # Enforce per-league epoch overrides (from configs/tracking_epochs.json)
                if not is_game_valid(league_id, file_date_str):
                    continue
                    
                league_name  = p.get("league", "Unknown")
                country      = p.get("country", "")
                
                # Key by league_id if available, fallback to unique composite string
                key = str(league_id) if league_id else f"{country}_{league_name}".upper()
                display_name = f"{country.upper()} — {league_name.upper()}" if country else league_name.upper()

                model_arch   = p.get("model_architecture", "[  SRS   ]")
                is_adv       = "ADVANCED" in (model_arch or "")
                
                # Apply Promotion logic
                if league_id in PROMOTE_SRS_TO_ADV:
                    model_key = "adv"
                else:
                    model_key = "adv" if is_adv else "srs"

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
                        "adv": _blank_model_stats(),
                        "system": _blank_model_stats()
                    }

                for t_name in [home_team, away_team]:
                    t_key = (t_name, str(league_id))
                    if t_key not in team_stats_dict:
                        team_stats_dict[t_key] = {
                            "name": t_name,
                            "league_id": league_id,
                            "league_name": display_name,
                            "srs": _blank_model_stats(),
                            "adv": _blank_model_stats(),
                            "system": _blank_model_stats()
                        }
                    
                # MAE Tracking
                total_delta = p.get("total_delta")
                if total_delta is not None and tier != "🚨 OT WARP":
                    # Specific model
                    stats_dict[key][model_key]["sum_delta"] += total_delta
                    stats_dict[key][model_key]["count_delta"] += 1
                    # Unified system
                    stats_dict[key]["system"]["sum_delta"] += total_delta
                    stats_dict[key]["system"]["count_delta"] += 1
                    for t_name in [home_team, away_team]:
                        t_key = (t_name, str(league_id))
                        team_stats_dict[t_key][model_key]["sum_delta"] += total_delta
                        team_stats_dict[t_key][model_key]["count_delta"] += 1
                        team_stats_dict[t_key]["system"]["sum_delta"] += total_delta
                        team_stats_dict[t_key]["system"]["count_delta"] += 1

                _tally(stats_dict[key][model_key],
                       pred_1x2, actual_1x2, tier, rpe, signed_delta)
                _tally(stats_dict[key]["system"],
                       pred_1x2, actual_1x2, tier, rpe, signed_delta)
                       
                for t_name in [home_team, away_team]:
                    t_key = (t_name, str(league_id))
                    _tally(team_stats_dict[t_key][model_key],
                           pred_1x2, actual_1x2, tier, rpe, signed_delta)
                    _tally(team_stats_dict[t_key]["system"],
                           pred_1x2, actual_1x2, tier, rpe, signed_delta)

                # Halftime tracking
                ht_pct = p.get("halftime_pct_of_model")
                if ht_pct is not None:
                    # Specific model
                    stats_dict[key][model_key]["ht_count"]   += 1
                    stats_dict[key][model_key]["ht_pct_sum"] += ht_pct
                    if ht_pct >= 50.0:
                        stats_dict[key][model_key]["ht_on_pace"] += 1
                    # Unified system
                    stats_dict[key]["system"]["ht_count"]   += 1
                    stats_dict[key]["system"]["ht_pct_sum"] += ht_pct
                    if ht_pct >= 50.0:
                        stats_dict[key]["system"]["ht_on_pace"] += 1

                    for t_name in [home_team, away_team]:
                        t_key = (t_name, str(league_id))
                        team_stats_dict[t_key][model_key]["ht_count"]   += 1
                        team_stats_dict[t_key][model_key]["ht_pct_sum"] += ht_pct
                        if ht_pct >= 50.0:
                            team_stats_dict[t_key][model_key]["ht_on_pace"] += 1
                        # Unified system
                        team_stats_dict[t_key]["system"]["ht_count"]   += 1
                        team_stats_dict[t_key]["system"]["ht_pct_sum"] += ht_pct
                        if ht_pct >= 50.0:
                            team_stats_dict[t_key]["system"]["ht_on_pace"] += 1

                # Hit Rate tracking (-5 pt buffer floor)
                act_h = p.get("actual_home_score")
                act_a = p.get("actual_away_score")
                model_total = p.get("model_total")
                if act_h is not None and act_a is not None and model_total:
                    actual_total = act_h + act_a
                    hit = 1 if actual_total >= (model_total - 5.0) else 0
                    # League level
                    stats_dict[key][model_key]["flat_floor_hits"]  += hit
                    stats_dict[key][model_key]["flat_floor_total"] += 1
                    stats_dict[key]["system"]["flat_floor_hits"]   += hit
                    stats_dict[key]["system"]["flat_floor_total"]  += 1
                    # Team level
                    for t_name in [home_team, away_team]:
                        t_key = (t_name, str(league_id))
                        team_stats_dict[t_key][model_key]["flat_floor_hits"]  += hit
                        team_stats_dict[t_key][model_key]["flat_floor_total"] += 1
                        team_stats_dict[t_key]["system"]["flat_floor_hits"]   += hit
                        team_stats_dict[t_key]["system"]["flat_floor_total"]  += 1

    except Exception as e:
        print(f"Error processing {os.path.basename(file_path)}: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Aggregate historical basketball performance stats.")
    parser.add_argument("--date", help="End date (YYYY-MM-DD) for aggregation. Only files on or before this date are included.")
    parser.add_argument("--verbose", action="store_true", help="Print names of processed files")
    args = parser.parse_args()

    print("Aggregating historical basketball league performance...")
    search_pattern = os.path.join(DATA_DIR, "universal_predictions_*_v2.json")
    all_files = glob.glob(search_pattern)
    
    # Filter files by Tracking Epoch and explicit user flags
    files = []
    
    start_dt = datetime.strptime(get_earliest_epoch(), "%Y-%m-%d")
    end_dt   = datetime.strptime(args.date, "%Y-%m-%d") if args.date else None
    
    for f in all_files:
        file_date_str = os.path.basename(f).replace("universal_predictions_", "").replace("_v2.json", "")
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
        print("No prediction files found valid for the tracking epoch.")

    league_stats = {}
    team_stats = {}
    
    for f in sorted(files):
        file_date_str = os.path.basename(f).replace("universal_predictions_", "").replace("_v2.json", "")
        if args.verbose:
            print(f" - Processing {os.path.basename(f)}...")
        process_file(f, file_date_str, league_stats, team_stats)
        
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

        return {
            "mape":              round(s["sum_rpe"] / count_rpe, 2) if count_rpe else 0.0,
            "mae":               round(s.get("sum_delta", 0) / count_delta, 2) if count_delta else None,
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
            # Hit Rate (-5 pt buffer)
            "flat_floor_hits":   s.get("flat_floor_hits", 0),
            "flat_floor_total":  s.get("flat_floor_total", 0),
            "flat_floor_rate":   round(s["flat_floor_hits"] / s["flat_floor_total"], 4) if s.get("flat_floor_total", 0) > 0 else None,
            # Halftime metrics (None until grader starts populating halftime fields)
            "avg_ht_pace":       round(s["ht_pct_sum"] / s["ht_count"], 1) if s.get("ht_count", 0) > 0 else None,
            "ht_on_pace_rate":   round(s["ht_on_pace"] / s["ht_count"] * 100, 1) if s.get("ht_count", 0) > 0 else None,
            "ht_graded_count":   s.get("ht_count", 0),
        }

    for key, models in league_stats.items():
        srs = _compile_model(models["srs"])
        adv = _compile_model(models["adv"])
        sys_m = _compile_model(models["system"])
        
        # System is now primary for overall reliability tracking
        primary = sys_m

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
            "outcome_w":          primary["outcome_w"],
            "outcome_l":          primary["outcome_l"],
            "outcome_hit_rate":   primary["outcome_hit_rate"],
            "srs":  srs if srs["graded_totals"] > 0 else None,
            "adv":  adv if adv["graded_totals"] > 0 else None,
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
        sys_m = _compile_model(models["system"])
        primary = sys_m

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
            "outcome_w":          primary["outcome_w"],
            "outcome_l":          primary["outcome_l"],
            "outcome_hit_rate":   primary["outcome_hit_rate"],
            # Hit Rate (-5 pt buffer, primary scoring input for confidence engine)
            "flat_floor_hits":    primary.get("flat_floor_hits", 0),
            "flat_floor_total":   primary.get("flat_floor_total", 0),
            "flat_floor_rate":    primary.get("flat_floor_rate"),
            "srs":  srs if srs["graded_totals"] > 0 else None,
            "adv":  adv if adv["graded_totals"] > 0 else None,
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
