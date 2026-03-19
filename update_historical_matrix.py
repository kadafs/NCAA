import os
import json
import sys
import requests
from datetime import datetime, timedelta, timezone

load_dotenv = None
try:
    from dotenv import load_dotenv
except ImportError:
    pass

if load_dotenv:
    load_dotenv()

API_KEY = os.getenv("API_BASKETBALL_KEY", "")
BASE_URL = "https://v1.basketball.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

def fuzzy_match(api_name, flashscore_team_list):
    """
    Intelligently maps a translated API string (e.g. 'Guaiqueries de Margarita') 
    mathematically back to the original localized Flashscore exact string ('Guaiqueries').
    """
    if not api_name or not flashscore_team_list: return None
    api_lower = api_name.lower().strip()
    
    # 1. Exact direct matches
    for ft in flashscore_team_list:
        if ft.lower() == api_lower: return ft
        
    # 2. Hard Partial Intersection
    for ft in flashscore_team_list:
        ft_lower = ft.lower()
        if ft_lower in api_lower or api_lower in ft_lower: return ft
        
    # 3. Aggressive Token Overlap Scoring
    api_tokens = set(api_lower.split())
    best_match = None
    best_score = 0
    for ft in flashscore_team_list:
        ft_tokens = set(ft.lower().split())
        overlap = len(api_tokens & ft_tokens)
        if overlap > best_score:
            best_score = overlap
            best_match = ft
            
    if best_score > 0:
        return best_match
        
    return None

def run_daily_delta():
    print(f"\n===========================================================")
    print("  INITIALIZING PHASE 22: CONTINUOUS DELTA MATRIX HEALING")
    print(f"===========================================================")
    
    # Normally this runs at 1:00 AM the next day. We fetch yesterday's physical dates manually.
    yesterday_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
    # If a date is explicitly provided via command line, use it!
    if len(sys.argv) > 1 and len(sys.argv[1]) == 10:
        yesterday_str = sys.argv[1]
        
    print(f"-> Querying finalized global outcomes for: {yesterday_str}")
    
    try:
        r = requests.get(
            f"{BASE_URL}/games",
            headers=HEADERS,
            params={"date": yesterday_str},
            timeout=15,
        )
        api_payload = r.json()
        games = api_payload.get("response", [])
        print(f"-> Harvested {len(games)} physical fixtures from Universal endpoint.")
    except Exception as e:
        print(f"-> FATAL: Could not fetch daily Delta array: {e}")
        sys.exit(1)
        
    map_file = "data/league_slug_map.json"
    slug_map = {}
    if os.path.exists(map_file):
        with open(map_file, encoding="utf-8") as f:
            slug_map = json.load(f)
            
    # Reverse map: {league_id: slug}
    id_to_slug = {v: k for k, v in slug_map.items()}
    
    successful_appends = 0
    skipped_appends = 0
    
    # Sort API games cleanly by active league IDs natively
    from collections import defaultdict
    league_sorted_games = defaultdict(list)
    for g in games:
        # Only inject fully finalized matches into Ridge Regression matrices natively
        status = g.get("status", {}).get("short", "")
        if status not in ["FT", "AOT"]: continue
        
        lid = g.get("league", {}).get("id")
        if lid: league_sorted_games[lid].append(g)
        
    for lid, finished_games in league_sorted_games.items():
        if lid not in id_to_slug: continue
        
        slug = id_to_slug[lid]
        target_path = f"data/historical/flashscore_{slug}.json"
        if not os.path.exists(target_path): continue
            
        with open(target_path, "r", encoding="utf-8") as f:
            local_matrix = json.load(f)
            
        native_games = local_matrix.get("games", [])
        if not native_games: continue
        
        # Build strict fuzzy-dictionary cache of all known Flashscore teams existing in this specific league
        known_teams = set()
        for hg in native_games:
            known_teams.add(hg.get("home_team"))
            known_teams.add(hg.get("away_team"))
            
        known_teams = list(filter(None, known_teams))
        
        # Inject API outcomes
        new_injections = 0
        for g in finished_games:
            hs = g.get("scores", {}).get("home", {}).get("total")
            as_ = g.get("scores", {}).get("away", {}).get("total")
            api_home = g.get("teams", {}).get("home", {}).get("name")
            api_away = g.get("teams", {}).get("away", {}).get("name")
            
            if not hs or not as_ or not api_home or not api_away:
                continue
                
            native_home = fuzzy_match(api_home, known_teams)
            native_away = fuzzy_match(api_away, known_teams)
            
            if not native_home or not native_away:
                skipped_appends += 1
                continue
                
            # Prevent physically generating redundant dataset duplicates inherently
            is_dup = False
            for prev_g in native_games[-30:]:
                if prev_g.get("home_team") == native_home and prev_g.get("away_team") == native_away:
                    if prev_g.get("home_score") == hs and prev_g.get("away_score") == as_:
                        is_dup = True
                        break
                        
            if not is_dup:
                native_games.append({
                    "date": g.get("date", "")[:10],
                    "home_team": native_home,
                    "away_team": native_away,
                    "home_score": int(hs),
                    "away_score": int(as_),
                    # We inject a proprietary delta flag so historical tracking algorithms strictly differentiate origin sources natively
                    "model_integrity": "[DELTA UPDATE]"
                })
                new_injections += 1
                successful_appends += 1
                
        if new_injections > 0:
            local_matrix["games"] = native_games
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(local_matrix, f, indent=4)
            print(f"  -> Injected {new_injections} organic regression scores into {slug}")
            
    print(f"\n===========================================================")
    print(f"-> CONTINUOUS LEARNING: Phase 22 Self-Healing Complete!")
    print(f"-> Mathematically Appended: {successful_appends} finalized outcomes natively.")
    print(f"-> Ignored: {skipped_appends} due to translation safety protocols.")
    print(f"===========================================================")

if __name__ == "__main__":
    run_daily_delta()
