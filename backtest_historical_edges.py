import json
import os
import glob
import math

def build_thresholds():
    print(f"\n===========================================================")
    print("  INITIALIZING PHASE 21: LEAGUE-SPECIFIC EDGE THRESHOLD BACKTESTER")
    print(f"===========================================================")
    
    map_file = "data/league_slug_map.json"
    if not os.path.exists(map_file):
        print("Missing league_slug_map.json! Run Phase 19 first.")
        return
        
    with open(map_file, encoding="utf-8") as f:
        slug_map = json.load(f)
        
    historical_files = glob.glob("data/historical/flashscore_*.json")
    thresholds = {}
    
    success_count = 0
    total_games_tested = 0
    
    for hf in historical_files:
        basename = os.path.basename(hf) 
        slug = basename.replace("flashscore_", "").replace(".json", "")
        
        league_id = slug_map.get(slug)
        if not league_id: continue
            
        stats_file = f"data/bball_stats_{league_id}.json"
        config_file = f"configs/leagues/{league_id}.json"
        
        if not os.path.exists(stats_file) or not os.path.exists(config_file):
            continue
            
        # 1. Load the True Offense Matrix we just built in Phase 20
        with open(stats_file, encoding="utf-8") as f:
            stats_data = json.load(f)
            teams_array = stats_data.get("teams", [])
            team_stats = {t["team_name"]: t for t in teams_array}
            
        # 2. Load the Pace & HCA Baseline we built in Phase 19
        with open(config_file, encoding="utf-8") as f:
            league_config = json.load(f)
            hca = league_config.get("hca_value", 3.0)
            
        # 3. Load the Actual Historical Games
        with open(hf, encoding="utf-8") as f:
            historical_data = json.load(f)
            games = historical_data.get("games", [])
            
        if not games or len(team_stats) == 0: continue
        
        error_sum = 0.0
        testable_games = 0
        
        # 4. Spin the Engine Math Backwards
        for g in games:
            hs = g.get("home_score", 0)
            as_ = g.get("away_score", 0)
            ht = g.get("home_team")
            at = g.get("away_team")
            
            if hs == 0 or as_ == 0 or ht not in team_stats or at not in team_stats:
                continue
                
            actual_total = hs + as_
            
            ht_o = team_stats[ht].get("adj_off", 0)
            ht_d = team_stats[ht].get("adj_def", 0)
            at_o = team_stats[at].get("adj_off", 0)
            at_d = team_stats[at].get("adj_def", 0)
            
            if ht_o == 0 or at_o == 0: continue
            
            # Replicate the UniversalBasketballEngine Math dynamically
            proj_home = ((ht_o + at_d) / 2) + (hca / 2)
            proj_away = ((at_o + ht_d) / 2) - (hca / 2)
            proj_total = proj_home + proj_away
            
            # Compute Absolute Error Margin
            absolute_error = abs(actual_total - proj_total)
            error_sum += absolute_error
            testable_games += 1
            total_games_tested += 1
            
        if testable_games < 10: continue
        
        # Mean Absolute Error mathematically establishes the precise volatility of the local league
        mae = error_sum / testable_games
        
        # The Custom Minimum Betting Edge Threshold (M.B.E.T.) is the MAE scaled logically (+20% safety margin)
        # Any mathematical discrepancies below the M.B.E.T are statistically categorized as random noise
        recommended_edge = round(mae * 1.2, 1)
        
        thresholds[str(league_id)] = {
            "slug": slug,
            "mean_absolute_error_pts": round(mae, 1),
            "recommended_minimum_edge": recommended_edge,
            "backtest_sample_size": testable_games
        }
        
        success_count += 1
        
    os.makedirs("configs", exist_ok=True)
    with open("configs/league_edge_thresholds.json", "w", encoding="utf-8") as f:
        json.dump(thresholds, f, indent=4)
        
    print(f"-> Mathematically backtested {total_games_tested} chronological physical matches.")
    print(f"-> Successfully established Minimum Betting Edge Thresholds (M.B.E.T) for {success_count} global leagues!")
    print(f"-> Exported matrix universally into: configs/league_edge_thresholds.json")
    print(f"===========================================================")

if __name__ == "__main__":
    build_thresholds()
