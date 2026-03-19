import json
import os
import glob

def calibrate():
    print(f"\n===========================================================")
    print("  INITIALIZING BASELINE AUTO-CALIBRATION MATRIX")
    print(f"===========================================================")
    
    map_file = "data/league_slug_map.json"
    if not os.path.exists(map_file):
        print("Missing league_slug_map.json! Please run python build_league_map.py first.")
        return
        
    with open(map_file, encoding="utf-8") as f:
        slug_map = json.load(f)
        
    historical_files = glob.glob("data/historical/flashscore_*.json")
    print(f"-> Discovered {len(historical_files)} historical datasets resting on disk.")
    
    os.makedirs("configs/leagues", exist_ok=True)
    calibrated_count = 0
    
    for hf in historical_files:
        basename = os.path.basename(hf) 
        slug = basename.replace("flashscore_", "").replace(".json", "")
        
        league_id = slug_map.get(slug)
        if not league_id:
            # Silently skip items not perfectly bridged in the mapped API block
            continue
            
        with open(hf, encoding="utf-8") as f:
            data = json.load(f)
            
        games = data.get("games", [])
        if len(games) < 5:
            continue
            
        total_points = 0
        home_wins = 0
        home_margin = 0
        total_games = 0
        
        for g in games:
            hs = g.get("home_score", 0)
            as_ = g.get("away_score", 0)
            if hs == 0 and as_ == 0: continue
            
            total_points += (hs + as_)
            home_margin += (hs - as_)
            if hs > as_:
                home_wins += 1
            total_games += 1
            
        if total_games == 0: continue
            
        # Core Auto-Calibrate Mathematics
        avg_pace = total_points / total_games
        avg_hca = home_margin / total_games
        
        # Load existing config if it legally exists so we don't accidentally purge manual overrides
        config_path = f"configs/leagues/{league_id}.json"
        config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, encoding="utf-8") as f:
                    config = json.load(f)
            except: pass
            
        config["pace_pivot"] = round(avg_pace, 1)                      # Expected combined points
        config["eff_pivot"] = round((avg_pace / 2) / 100, 3)           # Default efficiency ratio mapping
        config["hca_value"] = round(avg_hca, 1)                        # Mathematical home court advantage margin
        config["auto_calibrated"] = True
        config["calibration_games"] = total_games
        config["flashscore_slug"] = slug
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
            
        calibrated_count += 1
        
    print(f"-> Successfully auto-calibrated {calibrated_count} massive pure baseline endpoints globally!")
    print(f"===========================================================")

if __name__ == "__main__":
    calibrate()
