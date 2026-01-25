import os
import json
import argparse
from datetime import datetime
import zoneinfo
from nba_api.stats.endpoints import scoreboardv3
import sys

# Root addition for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mapping import get_target_date

# Base paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
MATCHUP_FILE = os.path.join(ROOT_DIR, "data", "nba_matchups.json")

def fetch_nba_daily_schedule(target_date=None):
    if target_date is None:
        target_date = get_target_date()
    
    date_str = target_date.strftime("%Y-%m-%d")
    print(f"Fetching NBA schedule for {date_str}...")
    
    try:
        # ScoreboardV3 is the newer, flat structure endpoint
        custom_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.nba.com/',
            'Origin': 'https://www.nba.com',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }
        
        sb = scoreboardv3.ScoreboardV3(game_date=date_str, headers=custom_headers, timeout=30)
        data = sb.get_dict()
        
        games = data.get('scoreboard', {}).get('games', [])
        
        matchups = []
        for g in games:
            home = g['homeTeam']
            away = g['awayTeam']
            
            # Status text like "7:00 pm ET" or "Final"
            status = g.get('gameStatusText', 'Scheduled')
            
            matchups.append({
                "away": away['teamName'],
                "home": home['teamName'],
                "away_city": away['teamCity'],
                "home_city": home['teamCity'],
                "game_time": status
            })
            
        print(f"Found {len(matchups)} games for {date_str}.")
        
        with open(MATCHUP_FILE, "w", encoding="utf-8") as f:
            json.dump(matchups, f, indent=2)
            
        return matchups

    except Exception as e:
        print(f"Error fetching NBA schedule: {e}")
        return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format")
    args = parser.parse_args()
    
    target = get_target_date(args.date)
    fetch_nba_daily_schedule(target)
