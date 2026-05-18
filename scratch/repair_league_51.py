import json
import glob
import os

def repair():
    print("Starting repair of past prediction files for League 51...")
    
    # 1. Load active stats for League 51 (both srs and adv if available)
    stats_map = {}
    for suffix in ["srs", "adv"]:
        fpath = f"data/bball_stats_51_{suffix}.json"
        if os.path.exists(fpath):
            try:
                with open(fpath, encoding="utf-8") as f:
                    data = json.load(f)
                    for t in data.get("teams", []):
                        name = t["team_name"]
                        if name not in stats_map:
                            stats_map[name] = t
            except Exception as e:
                print(f"Error loading {fpath}: {e}")
                
    print(f"Loaded stats for {len(stats_map)} teams in League 51.")

    # 2. Iterate through all universal predictions files
    pred_files = glob.glob("data/basketball/universal_predictions_*.json")
    repaired_count = 0
    
    for fpath in pred_files:
        modified = False
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            
            for p in data.get("predictions", []):
                if p.get("league_id") == 51:
                    home = p.get("home_team")
                    away = p.get("away_team")
                    
                    # Check and repair Home Team volatility
                    if p.get("home_team_volatility") is None and home in stats_map:
                        vol = stats_map[home].get("std_dev_totals")
                        if vol:
                            p["home_team_volatility"] = vol
                            modified = True
                            print(f"[{os.path.basename(fpath)}] Repaired {home} home volatility -> {vol}")
                            
                    # Check and repair Away Team volatility
                    if p.get("away_team_volatility") is None and away in stats_map:
                        vol = stats_map[away].get("std_dev_totals")
                        if vol:
                            p["away_team_volatility"] = vol
                            modified = True
                            print(f"[{os.path.basename(fpath)}] Repaired {away} away volatility -> {vol}")
                            
            if modified:
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                repaired_count += 1
                
        except Exception as e:
            print(f"Error processing {fpath}: {e}")
            
    print(f"Successfully repaired {repaired_count} files.")

if __name__ == "__main__":
    repair()
