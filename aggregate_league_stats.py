import json
import os
import glob
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "football")
OUTPUT_FILE = os.path.join(DATA_DIR, "league_leaderboard.json")
TEAM_OUTPUT_FILE = os.path.join(DATA_DIR, "football_leaderboard.json")

# ==========================================
# TRACKING EPOCH RESET
# Set back to 2020-01-01 to include all legacy/history graded data.
# The dashboard leaderboard will aggregate predictions from this date forward.
# ==========================================
TRACKING_EPOCH = "2020-01-01"

def _blank_stats():
    return {
        "btts_yes_w": 0, "btts_yes_l": 0,
        "btts_no_w": 0, "btts_no_l": 0,
        "draw_w": 0, "draw_l": 0,
        "1x2_w": 0, "1x2_l": 0,
        "bullseyes": 0, "excellents": 0, "solids": 0,
        "misses": 0, "busts": 0,
        "sum_delta": 0.0, "count_delta": 0,
        "sum_signed_delta": 0.0, "count_signed_delta": 0
    }

def _tally(bucket, pred_1x2, actual_1x2, decision, actual_btts, d_flag, actual_draw, tier, delta, signed_delta):
    """Add one prediction's data into a stats bucket."""
    is_1x2_win = (pred_1x2 == actual_1x2)
    if pred_1x2 and actual_1x2:
        if is_1x2_win: bucket["1x2_w"] += 1
        else:          bucket["1x2_l"] += 1
        
    if decision == "PLAY YES" and actual_btts is not None:
        if actual_btts: bucket["btts_yes_w"] += 1
        else:           bucket["btts_yes_l"] += 1
    elif decision in ("PLAY NO", "[STRONG] PLAY NO") and actual_btts is not None:
        if not actual_btts: bucket["btts_no_w"] += 1
        else:               bucket["btts_no_l"] += 1
            
    if d_flag and actual_draw is not None:
        if actual_draw: bucket["draw_w"] += 1
        else:           bucket["draw_l"] += 1

    if tier == "🎯 BULLSEYE":    bucket["bullseyes"]  += 1
    elif tier == "🟢 EXCELLENT": bucket["excellents"] += 1
    elif tier == "🟡 SOLID":    bucket["solids"]     += 1
    elif tier == "🟠 MISS":     bucket["misses"]     += 1
    elif tier == "🔴 BUST":     bucket["busts"]      += 1
    
    if delta is not None:
        bucket["sum_delta"] += delta
        bucket["count_delta"] += 1
    if signed_delta is not None:
        bucket["sum_signed_delta"] += signed_delta
        bucket["count_signed_delta"] += 1

def process_file(file_path, stats_dict, team_stats_dict):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        predictions = data.get("predictions", [])
        
        for p in predictions:
            if p.get("actual_result") is None:
                continue
                
            league_id   = p.get("league_id")
            league_name = p.get("league", "Unknown").upper()
            country     = p.get("country", "").upper()
            
            home_team = p.get("home_team", "Unknown")
            away_team = p.get("away_team", "Unknown")
            
            decision = p.get("btts_decision")
            d_flag = p.get("draw_value_flag", False)
            actual_btts = p.get("actual_btts")
            actual_draw = p.get("actual_draw")
            pred_1x2 = p.get("predicted_result")
            actual_1x2 = p.get("actual_result")
            
            tier = p.get("accuracy_tier")
            total_delta = p.get("total_delta")
            signed_delta = p.get("signed_delta")

            if country:
                display_name = f"{country} — {league_name}"
            else:
                display_name = league_name

            key = str(league_id) if league_id else display_name
            
            if key not in stats_dict:
                stats_dict[key] = {
                    "league_id": league_id,
                    "name": display_name,
                    "stats": _blank_stats()
                }
                
            for t_name in [home_team, away_team]:
                if t_name not in team_stats_dict:
                    team_stats_dict[t_name] = {
                        "name": t_name,
                        "league_id": league_id,
                        "league_name": display_name,
                        "stats": _blank_stats()
                    }

            _tally(stats_dict[key]["stats"], pred_1x2, actual_1x2, decision, actual_btts, d_flag, actual_draw, tier, total_delta, signed_delta)
            
            for t_name in [home_team, away_team]:
                _tally(team_stats_dict[t_name]["stats"], pred_1x2, actual_1x2, decision, actual_btts, d_flag, actual_draw, tier, total_delta, signed_delta)

    except Exception as e:
        print(f"Error processing {os.path.basename(file_path)}: {e}")

def _compile_metrics(s, base_info):
    b_w = s["btts_yes_w"] + s["btts_no_w"]
    b_l = s["btts_yes_l"] + s["btts_no_l"]
    b_total = b_w + b_l
    roi = 0.0
    hit_rate = 0.0
    if b_total > 0:
        roi = (b_w * 0.909) - b_l
        hit_rate = (b_w / b_total) * 100
        
    x_w = s["1x2_w"]
    x_l = s["1x2_l"]
    x_total = x_w + x_l
    x_hit_rate = (x_w / x_total * 100) if x_total > 0 else 0.0
    
    count_d = s["count_delta"]
    count_sd = s["count_signed_delta"]
    
    metrics = {
        "btts_plays": b_total,
        "btts_w": b_w, "btts_l": b_l,
        "btts_hit_rate": round(hit_rate, 1),
        "btts_roi": round(roi, 2),
        "draw_w": s["draw_w"], "draw_l": s["draw_l"],
        "outcome_w": x_w, "outcome_l": x_l,
        "outcome_hit_rate": round(x_hit_rate, 1),
        "mae": round(s["sum_delta"] / count_d, 2) if count_d else None,
        "avg_signed_delta": round(s["sum_signed_delta"] / count_sd, 2) if count_sd else None,
        "bullseyes": s["bullseyes"],
        "excellents": s["excellents"],
        "solids": s["solids"],
        "misses": s["misses"],
        "busts": s["busts"],
        "graded_totals": count_d
    }
    metrics.update(base_info)
    return metrics

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Aggregate historical football performance stats.")
    parser.add_argument("--date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print("Aggregating historical league & team performance...")
    search_pattern = os.path.join(DATA_DIR, "universal_predictions_*.json")
    all_files = glob.glob(search_pattern)
    
    start_dt = datetime.strptime(TRACKING_EPOCH, "%Y-%m-%d")
    end_dt   = datetime.strptime(args.date, "%Y-%m-%d") if args.date else None
    
    files = []
    for f in all_files:
        file_date_str = os.path.basename(f).replace("universal_predictions_", "").replace(".json", "")
        try:
            file_dt = datetime.strptime(file_date_str, "%Y-%m-%d")
            # 1. Enforce Tracking Epoch
            if file_dt < start_dt:
                continue
            # 2. Enforce explicit end date if passed
            if end_dt and file_dt > end_dt:
                continue
            files.append(f)
        except ValueError:
            continue

    if not files:
        print(f"No prediction files found valid for tracking epoch (>= {TRACKING_EPOCH}).")

    league_stats = {}
    team_stats = {}
    
    for f in sorted(files):
        if args.verbose: print(f" - Processing {os.path.basename(f)}...")
        process_file(f, league_stats, team_stats)
        
    leaderboard = []
    for key, data in league_stats.items():
        entry = _compile_metrics(data["stats"], {"league_id": data.get("league_id"), "name": data["name"]})
        leaderboard.append(entry)
        
    leaderboard.sort(key=lambda x: x["btts_roi"], reverse=True)
    
    output_data = {
        "updated_at": datetime.now().isoformat(),
        "total_leagues": len(leaderboard),
        "leaderboard": leaderboard
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    team_leaderboard = []
    for key, data in team_stats.items():
        entry = _compile_metrics(data["stats"], {
            "name": data["name"],
            "league": data.get("league_name"),
            "league_id": data.get("league_id")
        })
        team_leaderboard.append(entry)
        
    team_leaderboard.sort(key=lambda x: (-x["btts_roi"], x["mae"] or 999))
    
    team_output_data = {
        "updated_at": datetime.now().isoformat(),
        "total_teams": len(team_leaderboard),
        "leaderboard": team_leaderboard
    }
    with open(TEAM_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(team_output_data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully aggregated {len(files)} files.")
    print(f"Tracked {len(leaderboard)} leagues into league_leaderboard.json.")
    print(f"Tracked {len(team_leaderboard)} teams into football_leaderboard.json.")

if __name__ == "__main__":
    main()
