import os
import json
import requests

# Base paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
PLAYER_STATS_FILE = os.path.join(ROOT_DIR, "data", "euro_player_stats.json")

def fetch_euro_player_stats():
    print("Fetching EuroLeague player statistics (v3 traditional per game)...")
    
    # URL for player stats
    url = "https://api-live.euroleague.net/v3/competitions/E/statistics/players/traditional?statisticMode=PerGame&phaseTypeCode=RS&limit=1000"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        players_raw = data.get('players', [])
        players_out = []
        for p in players_raw:
            player_info = p.get('player', {})
            team_info = player_info.get('team', {})
            
            players_out.append({
                "id": player_info.get('code'),
                "name": player_info.get('name'),
                "team": team_info.get('code'),
                "pts": p.get('pointsScored', 0),
                "reb": p.get('totalRebounds', 0),
                "ast": p.get('assists', 0),
                "gp": p.get('gamesPlayed', 0),
                "min": p.get('minutesPlayed', 0)
            })
            
        print(f"Processed stats for {len(players_out)} EuroLeague players.")
        
        with open(PLAYER_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(players_out, f, indent=2)
            
        return players_out

    except Exception as e:
        print(f"Error fetching EuroLeague player stats: {e}")
        return []

if __name__ == "__main__":
    fetch_euro_player_stats()
