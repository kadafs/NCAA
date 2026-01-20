import os
import json
import requests

# Base paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
DATA_DIR = os.path.join(ROOT_DIR, "data")
PLAYER_STATS_FILE = os.path.join(DATA_DIR, "eurocup_player_stats.json")

def fetch_eurocup_player_stats():
    print("Fetching EuroCup player statistics (v3 traditional)...")
    
    # Competition Code 'U' for EuroCup
    url = "https://api-live.euroleague.net/v3/competitions/U/statistics/players/traditional?statisticMode=PerGame&phaseTypeCode=RS&limit=1000&seasonCode=U2024"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        players = []
        for p in data.get('players', []):
            # Extract basic info and stats
            # Team code is nested: p['player']['team']['code']
            players.append({
                "id": p['player']['code'],
                "name": p['player']['name'],
                "team": p['player']['team']['code'],
                "pts": p.get('pointsScored', 0),
                "reb": p.get('totalRebounds', 0),
                "ast": p.get('assists', 0),
                "gp": p.get('gamesPlayed', 0),
                "min": p.get('minutesPlayed', "0:00")
            })
            
        print(f"Processed stats for {len(players)} EuroCup players.")
        
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            
        with open(PLAYER_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(players, f, indent=2)
            
        return players

    except Exception as e:
        print(f"Error fetching EuroCup player stats: {e}")
        return []

if __name__ == "__main__":
    fetch_eurocup_player_stats()
