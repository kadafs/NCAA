import requests
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mapping import get_target_date
load_dotenv()

API_KEY = os.getenv("API_BASKETBALL_KEY")
BASE_URL = "https://v1.basketball.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# NBL1 Men's Conference League IDs
NBL1_CONFERENCES = {
    "Central": 212,
    "East": 215,
    "North": 207,
    "South": 209,
    "West": 214
}

# Australian Eastern timezone for date matching
AU_TZ = ZoneInfo("Australia/Sydney")


def _get_season_for_date(target_date):
    """Determines the NBL1 season year for a given date.
    NBL1 season runs Mar-Sep, so games in Jan-Feb belong to previous year's season."""
    month = target_date.month
    year = target_date.year
    # If Jan/Feb, the season started the previous year
    if month <= 2:
        return year - 1
    return year


def fetch_nbl1_schedule(target_date=None, season=None):
    """
    Fetches NBL1 daily schedule across all 5 conferences via API-Basketball.
    Uses season-level fetch and filters locally by date since the API's
    date parameter doesn't reliably work for NBL1.
    """
    if not API_KEY:
        print("ERROR: API_BASKETBALL_KEY not found in .env")
        return []
    
    if target_date is None:
        target_date = get_target_date()
    
    target_date_str = target_date.strftime("%Y-%m-%d")
    
    if season is None:
        season = _get_season_for_date(target_date)
    
    print(f"Fetching NBL1 schedule for {target_date_str} (Season {season})...")
    
    daily_matchups = []
    
    for conf_name, league_id in NBL1_CONFERENCES.items():
        try:
            # Fetch all games for the season and filter locally
            r = requests.get(f"{BASE_URL}/games", headers=HEADERS, 
                           params={"league": league_id, "season": season})
            all_games = r.json().get("response", [])
            
            for game in all_games:
                # API returns dates in UTC like "2024-03-23T09:45:00+00:00"
                game_date_str = game.get("date", "")[:10]
                
                # Also check if the game date in Australian time matches target
                # Games played in Australia at night (e.g. 7pm AEST = 09:00 UTC)
                # could show as previous day in UTC
                game_timestamp = game.get("timestamp")
                if game_timestamp:
                    game_dt_au = datetime.fromtimestamp(game_timestamp, tz=AU_TZ)
                    game_date_au = game_dt_au.strftime("%Y-%m-%d")
                else:
                    game_date_au = game_date_str
                
                # Match on either UTC date or Australian date
                if game_date_str != target_date_str and game_date_au != target_date_str:
                    continue
                
                teams = game.get("teams", {})
                scores = game.get("scores", {})
                status = game.get("status", {})
                
                home = teams.get("home", {})
                away = teams.get("away", {})
                
                matchup = {
                    "game_id": game.get("id"),
                    "home_team": home.get("name"),
                    "away_team": away.get("name"),
                    "home_id": home.get("id"),
                    "away_id": away.get("id"),
                    "home_logo": home.get("logo", ""),
                    "away_logo": away.get("logo", ""),
                    "conference": conf_name,
                    "league_id": league_id,
                    "start_time": game.get("date"),
                    "status": status.get("long", ""),
                    "home_score": scores.get("home", {}).get("total"),
                    "away_score": scores.get("away", {}).get("total")
                }
                daily_matchups.append(matchup)
            
        except Exception as e:
            print(f"  Error fetching NBL1 {conf_name} schedule: {e}")
            continue
    
    print(f"Found {len(daily_matchups)} total NBL1 games for {target_date_str}.")
    
    # Save to data directory
    os.makedirs("data", exist_ok=True)
    with open("data/nbl1_matchups.json", "w") as f:
        json.dump(daily_matchups, f, indent=4)
    
    return daily_matchups


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch NBL1 daily schedule from API-Basketball")
    parser.add_argument("--date", help="Target date (YYYY-MM-DD)")
    parser.add_argument("--season", type=int, help="Season year")
    args = parser.parse_args()
    
    target = get_target_date(args.date)
    fetch_nbl1_schedule(target, season=args.season)
