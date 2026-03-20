"""
auto_update_historical.py
=========================
Automatically fetches yesterday's final games from API-Basketball 
and appends them directly into data/historical/api_basketball_{league_id}.json.
This obsoletes the need to manually run the flashscore scraper daily for [  SRS  ] leagues.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

load_dotenv()

API_BASKETBALL_KEY = os.getenv("API_BASKETBALL_KEY")
if not API_BASKETBALL_KEY:
    print("Missing API_BASKETBALL_KEY in .env!")
    sys.exit(1)

API_BASKETBALL_BASE = "https://v1.basketball.api-sports.io"
API_BASKETBALL_HEADERS = {"x-apisports-key": API_BASKETBALL_KEY}
ET_TZ = ZoneInfo("America/New_York")

def main():
    target_date = (datetime.now(ET_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"\n===========================================================")
    print(f"  API-BASKETBALL AUTO-UPDATER | Target Date: {target_date}")
    print(f"===========================================================")

    slug_map_path = "data/league_slug_map.json"
    if not os.path.exists(slug_map_path):
        print("Missing league_slug_map.json! Cannot map matches.")
        sys.exit(1)

    with open(slug_map_path, "r", encoding="utf-8") as f:
        slug_map = json.load(f)

    # We need a reverse map from ID -> slug (or we just group by ID directly)
    tracked_league_ids = set(slug_map.values())
    
    print(f"  Requesting ALL global games for {target_date}...")
    try:
        r = requests.get(
            f"{API_BASKETBALL_BASE}/games",
            headers=API_BASKETBALL_HEADERS,
            params={"date": target_date},
            timeout=15
        )
        data = r.json()
        if data.get("errors"):
            print(f"  [API Error] {data['errors']}")
            sys.exit(1)
            
        games = data.get("response", [])
        print(f"  Found {len(games)} total global games.")
        
    except Exception as e:
        print(f"  [Error] Could not fetch daily games: {e}")
        sys.exit(1)

    # Group valid games by League ID
    updates_by_league = {}
    valid_games_count = 0

    for game in games:
        # Check if the game is actually finished
        status = game.get("status", {}).get("short", "")
        if status not in ("FT", "AOT"):
            continue
            
        league_id = game.get("league", {}).get("id")
        if not league_id or league_id not in tracked_league_ids:
            continue

        teams = game.get("teams", {})
        scores = game.get("scores", {})
        
        home_name = teams.get("home", {}).get("name")
        away_name = teams.get("away", {}).get("name")
        home_score = scores.get("home", {}).get("total")
        away_score = scores.get("away", {}).get("total")
        
        if not all([home_name, away_name, home_score, away_score]):
            continue

        # Format it exactly like the historical flashscore/proballers parser expects
        clean_game = {
            "date": game.get("date", "")[:10],
            "home_team": home_name,
            "away_team": away_name,
            "home_score": home_score,
            "away_score": away_score,
            "game_id": game.get("id")
        }

        if league_id not in updates_by_league:
            updates_by_league[league_id] = []
        updates_by_league[league_id].append(clean_game)
        valid_games_count += 1

    print(f"  Extracted {valid_games_count} relevant games across {len(updates_by_league)} tracked leagues.")

    os.makedirs("data/historical", exist_ok=True)
    
    # Save the injected games
    injected_count = 0
    for lid, new_games in updates_by_league.items():
        file_path = f"data/historical/api_basketball_{lid}.json"
        
        existing_games = []
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_games = json.load(f)
            except Exception:
                existing_games = []

        # Avoid duplicates based on game_id
        existing_ids = {g.get("game_id") for g in existing_games if g.get("game_id")}
        added_for_league = 0
        
        for ng in new_games:
            if ng["game_id"] not in existing_ids:
                existing_games.append(ng)
                added_for_league += 1
                injected_count += 1

        if added_for_league > 0:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(existing_games, f, indent=4)
            print(f"  [League {lid}] Appended {added_for_league} new games.")

    print(f"\n  SUCCESS: Injected {injected_count} new historical games securely into the Database.")
    print(f"===========================================================\n")

if __name__ == "__main__":
    main()
