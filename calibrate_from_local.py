import os
import glob
import json
import datetime
import argparse

# Import the core math and config builders from the original calibrator!
from calibrate_league import derive_params, build_config, KNOWN_TIER_MAP
from generate_advanced_metrics import parse_date, CROSS_SOURCE_CANONICAL_MAP

def main():
    parser = argparse.ArgumentParser(description="Local Offline Calibrator")
    parser.add_argument("--league_id", type=int, help="Only calibrate this specific league ID")
    args = parser.parse_args()

    print("======================================================")
    print("  LOCAL BASKETBALL CALIBRATION (Bypassing API Limits) ")
    if args.league_id:
        print(f"  TARGET: League ID {args.league_id} Only")
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
    n_files = glob.glob("data/historical/nbl1_official_*.json")
    historical_files = f_files + p_files + a_files + n_files

    # 3. Use dynamic season detection per league based on schedule gaps (>75 days)
    # Removed the hardcoded August cutoff to support global summer/winter leagues
    
    # 4. Group the games by league_id, ensuring deduplication
    games_by_league = {}

    for hf in historical_files:
        basename = os.path.basename(hf) 
        slug = basename.replace("flashscore_", "").replace("proballers_", "").replace("api_basketball_", "").replace("nbl1_official_", "").replace(".json", "")
        
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
                    "home": home,
                    "away": away,
                    "_parsed_date": game_date
                })

        except Exception as e:
            print(f"Error reading {hf}: {e}")

    # 3.5. Gather all daily API cache files
    d_files = glob.glob("data/api_basketball_today_*.json")
    for df in d_files:
        try:
            with open(df, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            for entry in data.get("leagues_summary", []):
                league_id = entry.get("league_id")
                if not league_id:
                    continue
                    
                if league_id not in games_by_league:
                    games_by_league[league_id] = []
                    
                for g in entry.get("games", []):
                    h_score = g.get("home_score")
                    a_score = g.get("away_score")
                    
                    # Handle alternative string score format if needed
                    if h_score is None and a_score is None and g.get("score") and "-" in str(g["score"]):
                        parts = str(g["score"]).split("-")
                        if len(parts) == 2:
                            h_score = parts[0].strip()
                            a_score = parts[1].strip()
                            
                    if h_score is None or a_score is None:
                        continue
                        
                    try:
                        h_score = int(h_score)
                        a_score = int(a_score)
                    except ValueError:
                        continue
                        
                    total = h_score + a_score
                    margin = h_score - a_score
                    
                    home = str(g.get("home", "")).strip()
                    away = str(g.get("away", "")).strip()
                    
                    # Check for date or time
                    date_str = str(g.get("time") or g.get("date") or data.get("date") or "")
                    game_date = parse_date(date_str)
                    
                    # Skip awarded/forfeited matches — scores like 20-0 are not real game totals
                    if g.get("status") == "Game Awarded":
                        continue

                    # If game is scheduled but hasn't fully finished with a score we shouldn't have matched h_score
                    if h_score == 0 and a_score == 0 and g.get("status") not in ("Game Finished", "Final", "AOT", "FT"):
                        continue
                    
                    games_by_league[league_id].append({
                        "total": total,
                        "margin": margin,
                        "home": home,
                        "away": away,
                        "_parsed_date": game_date
                    })
        except Exception as e:
            print(f"Error reading {df}: {e}")

    # 4. Process the math for every league and save the configs
    os.makedirs("configs/leagues", exist_ok=True)
    success_count = 0
    
    for lid, all_games in games_by_league.items():
        if args.league_id and lid != args.league_id:
            continue
            
        valid_games = [g for g in all_games if g["_parsed_date"] > datetime.datetime.min]
        if not valid_games:
            continue

        # Apply cross-source canonical name mapping BEFORE fuzzy normalization.
        # Mirrors the same step in generate_advanced_metrics.py so the calibration
        # baseline is not inflated by the same game appearing under two different names.
        for g in valid_games:
            if g.get("home") in CROSS_SOURCE_CANONICAL_MAP:
                g["home"] = CROSS_SOURCE_CANONICAL_MAP[g["home"]]
            if g.get("away") in CROSS_SOURCE_CANONICAL_MAP:
                g["away"] = CROSS_SOURCE_CANONICAL_MAP[g["away"]]

        team_name_map = {}
        all_names = set()
        for g in valid_games:
            if g.get("home"): all_names.add(g.get("home"))
            if g.get("away"): all_names.add(g.get("away"))
            
        import difflib
        sorted_names = sorted(list(all_names), key=len, reverse=True)
        for name in sorted_names:
            matched = False
            name_lower = name.lower()
            for primary in set(team_name_map.values()):
                pri_lower = primary.lower()
                
                # Rule 1: Exact substring overlap
                if name_lower in pri_lower or pri_lower in name_lower:
                    team_name_map[name] = primary
                    matched = True
                    break
                    
                # Rule 2: High character overlap ratio via difflib
                similarity = difflib.SequenceMatcher(None, name_lower, pri_lower).ratio()
                if similarity >= 0.85:
                    team_name_map[name] = primary
                    matched = True
                    break
                    
            if not matched:
                team_name_map[name] = name
                
        # Clean out duplicates using normalized names
        unique_games = {}
        for g in valid_games:
            norm_home = team_name_map.get(g["home"], g["home"])
            norm_away = team_name_map.get(g["away"], g["away"])
            gid = f"{g['_parsed_date'].strftime('%Y-%m-%d')}_{norm_home}_{norm_away}_{g['total']}_{g['margin']}"
            unique_games[gid] = g
            
        merged_games = list(unique_games.values())
        merged_games.sort(key=lambda x: x["_parsed_date"])
        
        # Hard Date Cutoff Filter
        now = datetime.datetime.now()
        cur_year = now.year
        cur_month = now.month
        
        summer_league_ids = {"13", "66", "76", "222", "207", "208", "209", "210", "211", "212", "213", "214", "215", "216"}
        lid_str = str(lid)
        
        if lid_str in summer_league_ids:
            cutoff_date = datetime.datetime(cur_year, 1, 1)
        else:
            if cur_month >= 8:
                cutoff_date = datetime.datetime(cur_year, 8, 1)
            else:
                cutoff_date = datetime.datetime(cur_year - 1, 8, 1)
                
        final_games = [g for g in merged_games if g["_parsed_date"] >= cutoff_date]
        
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
        if derived or not existing_cfg:
            tier_name = KNOWN_TIER_MAP.get(lid, existing_cfg.get("_tier", "top_domestic"))
            
            # The heart of the magic:
            new_config = build_config(lid, league_name, derived, tier_name)
            
            # Carry over explicit edge variables if they were manually set
            for key in ["win_prob_std_dev", "situational", "thresholds"]:
                if key in existing_cfg:
                    new_config[key] = existing_cfg[key]
                    
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=2)

            # Compute and store _xpts_correction: bridges the gap between adj_off-derived
            # xPTS and the true calibrated league average scoring level.
            stats_file = f"data/bball_stats_{lid}_adv.json"
            if not os.path.exists(stats_file):
                stats_file = f"data/bball_stats_{lid}_srs.json"
            if os.path.exists(stats_file):
                try:
                    with open(stats_file, "r", encoding="utf-8") as sf:
                        stats_data = json.load(sf)
                    teams = stats_data.get("teams", [])
                    if len(teams) >= 2:
                        avg_adj_off = sum(t.get("adj_off", 0) for t in teams) / len(teams)
                        avg_adj_t   = sum(t.get("adj_t", derived.get("pace_pivot", 76.0)) for t in teams) / len(teams)
                        derived_avg_per_team = (avg_adj_off * avg_adj_t) / 100
                        target_per_team = derived["avg_total"] / 2
                        if derived_avg_per_team > 0:
                            correction = target_per_team / derived_avg_per_team
                            # Cap at ±25% to prevent over-correction
                            correction = max(0.75, min(1.25, correction))
                            if abs(correction - 1.0) > 0.02:
                                new_config["_xpts_correction"] = round(correction, 4)
                                with open(config_path, "w", encoding="utf-8") as f:
                                    json.dump(new_config, f, indent=2)
                                print(f"       xPTS Correction: {correction:.4f} (team avg xPts/team: {derived_avg_per_team:.1f}, target: {target_per_team:.1f})")
                except Exception as e:
                    print(f"       Warning: xPTS correction skipped for {lid}: {e}")

            success_count += 1
            if derived:
                print(f"  [+] Calibrated {lid:4d} ({league_name[:20]:20}) | {derived['n_games']:4d} games | Avg Tot: {derived['avg_total']:.1f}")
            else:
                print(f"  [+] Fallback   {lid:4d} ({league_name[:20]:20}) | < 10 games | Used Tier Template")

    print("======================================================")
    print(f"  SUCCESS! Locally Auto-Calibrated {success_count} leagues.")
    print("======================================================")

if __name__ == "__main__":
    main()
