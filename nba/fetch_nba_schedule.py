import os
import json
from datetime import datetime
import zoneinfo
from nba_api.live.nba.endpoints import scoreboard

# Base paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
MATCHUP_FILE = os.path.join(ROOT_DIR, "data", "nba_matchups.json")

def fetch_nba_daily_schedule():
    print("Fetching today's NBA schedule...")
    
    # Use ET for NBA (New York time)
    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    
    try:
        sb = scoreboard.ScoreBoard()
        data = sb.get_dict()
        
        games = data['scoreboard']['games']
        print(f"Found {len(games)} games for {now.strftime('%Y-%m-%d')}.")
        
        matchups = []
        for game in games:
            matchups.append({
                "away": game['awayTeam']['teamName'],
                "home": game['homeTeam']['teamName'],
                "away_city": game['awayTeam']['teamCity'],
                "home_city": game['homeTeam']['teamCity'],
                "game_time": game['gameStatusText']
            })
            
        with open(MATCHUP_FILE, "w") as f:
            json.dump(matchups, f, indent=2)
            
        return matchups

    except Exception as e:
        print(f"Error fetching NBA schedule: {e}")
        return []

if __name__ == "__main__":
    fetch_nba_daily_schedule()
