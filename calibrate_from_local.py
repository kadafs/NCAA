import os
import glob
import json
import datetime

# Import the core math and config builders from the original calibrator!
from calibrate_league import derive_params, build_config, KNOWN_TIER_MAP
from generate_advanced_metrics import parse_date

def main():
    print("======================================================")
    print("  LOCAL BASKETBALL CALIBRATION (Bypassing API Limits) ")
    print("======================================================")

    # 1. Load the slug map to identify leagues
    map_file = "data/league_slug_map.json"
    if not os.path.exists(map_file):
        print("Missing data/league_slug_map.json. Aborting.")
        return

    with open(map_file, "r", encoding="utf-8") as f:
        slug_map = json.load(f)

    # 2. Gather all historical JSON archives
    f_files = glob.glob("data/historical/flashscore_*.json")
    p_files = glob.glob("data/historical/proballers_*.json")
    a_files = glob.glob("data/historical/api_basketball_*.json")
    historical_files = f_files + p_files + a_files

    # 3. Use dynamic season detection per league based on schedule gaps (>75 days)
    # Removed the hardcoded August cutoff to support global summer/winter leagues
    
    # 4. Group the games by league_id, ensuring deduplication
    games_by_league = {}

    for hf in historical_files:
        basename = os.path.basename(hf) 
        slug = basename.replace("flashscore_", "").replace("proballers_", "").replace("api_basketball_", "").replace(".json", "")
        
        if slug.isdigit():
            league_id = int(slug)
        else:
            league_id = slug_map.get(slug)
            
        if not league_id:
            league_id = slug_map.get(slug.replace("-", "_"))
            if not league_id:
                continue

        try:
            with open(hf, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            games = data if isinstance(data, list) else data.get("games", [])
            if not games: 
                continue

            for g in games:
                h_score = g.get("home_score") or g.get("h_score")
                a_score = g.get("away_score") or g.get("a_score")
                
                # We need valid final scores to do math!
                if h_score is None or a_score is None:
                    continue
                try:
                    h_score = int(h_score)
                    a_score = int(a_score)
                except ValueError:
                    continue
                
                total = h_score + a_score
                margin = h_score - a_score
                
                if league_id not in games_by_league:
                    games_by_league[league_id] = []
                    
                # Deduplicate by looking at the match signature
                home = str(g.get("home") or g.get("home_team") or g.get("home_name", "")).strip()
                away = str(g.get("away") or g.get("away_team") or g.get("away_name", "")).strip()
                
                # Extract and parse date for dynamic season filtering later
                date_str = str(g.get("date") or g.get("match_time") or "")
                game_date = parse_date(date_str)
                
                sig = f"{home}_{away}_{total}_{margin}"
                games_by_league[league_id].append({
                    "total": total,
                    "margin": margin,
                    "sig": sig,
                    "_parsed_date": game_date
                })

        except Exception as e:
            print(f"Error reading {hf}: {e}")

    # 4. Process the math for every league and save the configs
    os.makedirs("configs/leagues", exist_ok=True)
    success_count = 0
    
    for lid, all_games in games_by_league.items():
        # Clean out duplicates
        unique_games = {}
        for g in all_games:
            unique_games[g["sig"]] = g
            
        merged_games = list(unique_games.values())
        
        # EXACT MATCH TO generate_advanced_metrics.py: Filter out unparseable dates
        merged_games = [g for g in merged_games if g["_parsed_date"] > datetime.datetime.min]
        merged_games.sort(key=lambda x: x["_parsed_date"])
        
        # Season Gap Filter: find LAST contiguous block of games (separated by > 75 days)
        last_gap_idx = 0
        for i in range(1, len(merged_games)):
            delta = (merged_games[i]["_parsed_date"] - merged_games[i-1]["_parsed_date"]).days
            if delta > 75:
                last_gap_idx = i
                
        final_games = merged_games[last_gap_idx:]
        
        # Load existing config for the league name if available
        league_name = f"League {lid}"
        config_path = f"configs/leagues/{lid}.json"
        existing_cfg = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    existing_cfg = json.load(f)
                    league_name = existing_cfg.get("name", league_name)
            except:
                pass

        # 5. Calculate parameters
        derived = derive_params(final_games, lid, league_name)
        
        # We process if we derived actual params or if the existing file is missing parameters entirely
        if derived:
            tier_name = KNOWN_TIER_MAP.get(lid, existing_cfg.get("_tier", "top_domestic"))
            
            # The heart of the magic:
            new_config = build_config(lid, league_name, derived, tier_name)
            
            # Carry over explicit edge variables if they were manually set
            for key in ["win_prob_std_dev", "situational", "thresholds"]:
                if key in existing_cfg:
                    new_config[key] = existing_cfg[key]
                    
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=2)
                
            success_count += 1
            print(f"  [+] Calibrated {lid:4d} ({league_name[:20]:20}) | {derived['n_games']:4d} games | Avg Tot: {derived['avg_total']:.1f}")

    print("======================================================")
    print(f"  SUCCESS! Locally Auto-Calibrated {success_count} leagues.")
    print("======================================================")

if __name__ == "__main__":
    main()
