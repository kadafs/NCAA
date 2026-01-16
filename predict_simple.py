import json
import os
import requests
import zoneinfo
from datetime import datetime

# Script 5: Simple Scoring Model
# Logic: Proj Score = (Team A Offense + Team B Defense) / 2
# Uses only basic Scoring Offense (PPG) and Scoring Defense (OPP PPG).

BASE_URLS = ["http://localhost:3005", "http://localhost:3000", "https://ncaa-api.henrygd.me"]
TEAM_STATS_FILE = "data/consolidated_stats.json"
BARTTORVIK_STATS_FILE = "data/barttorvik_stats.json"

def fetch_scoreboard(year, month, day):
    for base in BASE_URLS:
        url = f"{base}/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            continue
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

def find_barttorvik_team(name, barttorvik_dict):
    if not name or not barttorvik_dict: return None
    if name in barttorvik_dict: return name
    
    custom_map = {
        "St. Mary's (CA)": "Saint Mary's",
        "Saint Mary's (CA)": "Saint Mary's",
        "UConn": "Connecticut",
        "Ole Miss": "Mississippi",
        "UMKC": "Kansas City",
        "Penn": "Pennsylvania",
        "Fullerton": "Cal St. Fullerton",
        "Long Beach State": "Cal St. Long Beach",
        "Northridge": "Cal St. Northridge",
        "Bakersfield": "Cal St. Bakersfield",
        "St. Thomas (MN)": "St. Thomas",
        "UL Monroe": "Louisiana Monroe",
        "Louisiana": "Louisiana Lafayette",
    }
    if name in custom_map and custom_map[name] in barttorvik_dict:
        return custom_map[name]
        
    name_low = name.lower()
    for bt_name in barttorvik_dict:
        bt_low = bt_name.lower()
        if name_low == bt_low or name_low in bt_low or bt_low in name_low:
            return bt_name
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

def predict_simple(away_raw, home_raw, metrics):
    nameA = find_team(away_raw, metrics)
    nameH = find_team(home_raw, metrics)
    if not nameA or not nameH: return None
    
    tA, tH = metrics[nameA], metrics[nameH]
    
    # Simple Math: Average of Team A Offense and Team B Defense
    scoreA = (tA['offense'] + tH['defense']) / 2
    scoreH = (tH['offense'] + tA['defense']) / 2
    
    return {
        "scoreA": round(scoreA, 1),
        "scoreH": round(scoreH, 1),
        "total": round(scoreA + scoreH, 1),
        "spread": round(scoreH - scoreA, 1)
    }

def print_row(matchup, p_score, spread, adj_t, adj_oe, adj_de):
    print(f"{matchup:<35} | {p_score:<15} | {spread:<8} | {adj_t:<12} | {adj_oe:<12} | {adj_de:<12}")

def main():
    stats_data = load_json(TEAM_STATS_FILE)
    if not stats_data:
        print("Stats data missing.")
        return

    metrics = get_simple_metrics(stats_data)
    
    bt_stats = load_json(BARTTORVIK_STATS_FILE)
    if bt_stats:
        print(f"Loaded {len(bt_stats)} teams from BartTorvik for advanced metadata.")

    
    # Use current date in ET
    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    print(f"\n--- Simple Predictions for {now.strftime('%Y-%m-%d')} ---")
    print("(Based ONLY on PPG and OPP PPG averages)")
    
    board = fetch_scoreboard(now.year, now.month, now.day)
    if not board or 'games' not in board or not board['games']:
        print("No games found on scoreboard.")
        return

    print(f"{'Matchup':<35} | {'Proj Score':<15} | {'Spread':<8} | {'Adj T (A/H)':<12} | {'AdjOE (A/H)':<12} | {'AdjDE (A/H)':<12}")
    print("-" * 120)
    
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
            
            match_str = f"{away_raw} @ {home_raw}"
            score_str = f"{scoreA:.1f} - {scoreH:.1f}"
            spread_str = f"{scoreH - scoreA:+.1f}"
            
            # Metadata Lookup
            btA_name = find_barttorvik_team(away_raw, bt_stats)
            btH_name = find_barttorvik_team(home_raw, bt_stats)
            btA = bt_stats.get(btA_name) if btA_name else None
            btH = bt_stats.get(btH_name) if btH_name else None
            
            t_str = f"{round(btA['adj_t'], 1) if btA else 'N/A'} / {round(btH['adj_t'], 1) if btH else 'N/A'}"
            oe_str = f"{round(btA['adj_off'], 1) if btA else 'N/A'} / {round(btH['adj_off'], 1) if btH else 'N/A'}"
            de_str = f"{round(btA['adj_def'], 1) if btA else 'N/A'} / {round(btH['adj_def'], 1) if btH else 'N/A'}"
            
            print_row(match_str, score_str, spread_str, t_str, oe_str, de_str)

if __name__ == "__main__":
    main()
