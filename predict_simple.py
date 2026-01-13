import json
import os
import requests
from datetime import datetime

# Script 5: Simple Scoring Model
# Logic: Proj Score = (Team A Offense + Team B Defense) / 2
# Uses only basic Scoring Offense (PPG) and Scoring Defense (OPP PPG).

BASE_URL = "http://localhost:3000"
TEAM_STATS_FILE = "data/consolidated_stats.json"

def fetch_scoreboard(year, month, day):
    url = f"{BASE_URL}/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching scoreboard: {e}")
    return None

def load_json(path):
    if not os.path.exists(path): return None
    with open(path, "r") as f: return json.load(f)

def find_team(name, teams_dict):
    if not name: return None
    if name in teams_dict: return name
    standard_map = {
        "St. Mary's (CA)": "Saint Mary's (CA)",
        "St Mary's": "Saint Mary's (CA)",
        "Saint Mary's": "Saint Mary's (CA)",
        "UConn": "UConn", "Ole Miss": "Ole Miss", "UPenn": "Penn"
    }
    if name in standard_map: return standard_map[name]
    name_low = name.lower()
    for t_name in teams_dict:
        t_low = t_name.lower()
        if name_low == t_low or name_low in t_low or t_low in name_low:
            return t_name
    return None

def get_simple_metrics(stats_data):
    teams = {}
    for key in stats_data:
        if key not in ["scoring_offense", "scoring_defense"]:
            continue
        for entry in stats_data[key]:
            name = entry['Team']
            if name not in teams: teams[name] = {}
            
            if key == "scoring_offense":
                teams[name]['offense'] = float(entry.get('PPG', 0))
            elif key == "scoring_defense":
                teams[name]['defense'] = float(entry.get('OPP PPG', 0))
    
    # Filter only those with both stats
    valid_teams = {n: s for n, s in teams.items() if 'offense' in s and 'defense' in s}
    return valid_teams

def main():
    stats_data = load_json(TEAM_STATS_FILE)
    if not stats_data:
        print("Stats data missing.")
        return

    metrics = get_simple_metrics(stats_data)
    
    # Use current date
    now = datetime.now()
    print(f"\n--- Simple Predictions for {now.strftime('%Y-%m-%d')} ---")
    print("(Based ONLY on PPG and OPP PPG averages)")
    
    board = fetch_scoreboard(now.year, now.month, now.day)
    if not board or 'games' not in board or not board['games']:
        print("No games found on scoreboard.")
        return

    print(f"{'Matchup':<40} | {'Proj Score':<15} | {'Total':<10} | {'Spread':<10}")
    print("-" * 85)
    
    for game_wrapper in board['games']:
        game = game_wrapper.get('game')
        if not game: continue
        
        away_raw = game['away']['names']['short']
        home_raw = game['home']['names']['short']
        
        nameA = find_team(away_raw, metrics)
        nameH = find_team(home_raw, metrics)

        if nameA and nameH:
            tA, tH = metrics[nameA], metrics[nameH]
            
            # Simple Math: Average of Team A Offense and Team B Defense
            scoreA = (tA['offense'] + tH['defense']) / 2
            scoreH = (tH['offense'] + tA['defense']) / 2
            
            total = scoreA + scoreH
            spread = scoreH - scoreA
            
            match_str = f"{away_raw} @ {home_raw}"
            score_str = f"{scoreA:.1f} - {scoreH:.1f}"
            print(f"{match_str:<40} | {score_str:<15} | {total:<10.1f} | {spread:<10.1f}")

if __name__ == "__main__":
    main()
