import os
import json
import argparse
from datetime import datetime
import zoneinfo
from nba_api.stats.endpoints import scoreboardv2
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
        # scoreboardv2 is better for specific dates
        # Use custom headers to avoid blocks in GitHub Actions
        custom_headers = {
            'Host': 'stats.nba.com',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        sb = scoreboardv2.ScoreboardV2(game_date=date_str, headers=custom_headers, timeout=30)
        data = sb.get_dict()
        
        # In scoreboardv2, games are in 'GameHeader' rowSet
        headers = data['resultSets'][0]['headers']
        rows = data['resultSets'][0]['rowSet']
        
        # Map headers to indices
        idx_game_id = headers.index('GAME_ID')
        idx_home_id = headers.index('HOME_TEAM_ID')
        idx_away_id = headers.index('VISITOR_TEAM_ID')
        idx_status = headers.index('GAME_STATUS_TEXT')
        
        # Team info is in 'LineScore'
        ls_headers = data['resultSets'][1]['headers']
        ls_rows = data['resultSets'][1]['rowSet']
        
        idx_ls_team_id = ls_headers.index('TEAM_ID')
        idx_ls_team_name = ls_headers.index('TEAM_NAME')
        idx_ls_city = ls_headers.index('TEAM_CITY_NAME')
        
        team_map = {}
        for row in ls_rows:
            team_map[row[idx_ls_team_id]] = {
                "name": row[idx_ls_team_name],
                "city": row[idx_ls_city]
            }

        matchups = []
        for row in rows:
            home_team = team_map.get(row[idx_home_id], {"name": "Unknown", "city": "Unknown"})
            away_team = team_map.get(row[idx_away_id], {"name": "Unknown", "city": "Unknown"})
            
            matchups.append({
                "away": away_team['name'],
                "home": home_team['name'],
                "away_city": away_team['city'],
                "home_city": home_team['city'],
                "game_time": row[idx_status]
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
