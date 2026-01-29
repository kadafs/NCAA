import json
import os
import requests
import zoneinfo
from datetime import datetime
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES

# Script 5: Simple Scoring Model
# Logic: Proj Score = (Team A Offense + Team B Defense) / 2
# Uses only basic Scoring Offense (PPG) and Scoring Defense (OPP PPG).

BASE_URLS = ["http://localhost:3005", "http://localhost:3000", "https://ncaa-api.henrygd.me"]
# Base paths relative to Project Root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))

TEAM_STATS_FILE = os.path.join(ROOT_DIR, "data", "consolidated_stats.json")
BARTTORVIK_STATS_FILE = os.path.join(ROOT_DIR, "data", "barttorvik_stats.json")
INJURY_NOTES_FILE = os.path.join(ROOT_DIR, "data", "injury_notes.json")

def fetch_scoreboard(year, month, day):
    # Try local first, then external
    for base in BASE_URLS:
        url = f"{base}/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}"
        try:
            # Increased timeout to 15s to handle cold starts or slow networks
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                return response.json()
        except Exception:
            continue
    return None

def load_json(path):
    if not os.path.exists(path): return None
    with open(path, "r") as f: return json.load(f)

# Using shared find_team_in_dict from utils.mapping instead of local helpers

def find_injury_team(name, injury_dict):
    if not name or not injury_dict: return None
    # Action Network names are often "Team Name Mascot" e.g., "Alabama Crimson Tide"
    name_low = name.lower()
    for inj_team in injury_dict:
        inj_low = inj_team.lower()
        if name_low in inj_low or inj_low in name_low:
            return inj_team
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
    nameA = find_team_in_dict(away_raw, metrics, BASKETBALL_ALIASES)
    nameH = find_team_in_dict(home_raw, metrics, BASKETBALL_ALIASES)
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

def print_row(matchup, p_score, spread, conf, adj_t, efg, to, or_rate, ftr):
    # efg, to, or_rate, ftr are strings like "55.1 / 48.2"
    print(f"{matchup:<35} | {p_score:<15} | {spread:<8} | {conf:<10} | {adj_t:<11} | {efg:<12} | {to:<12} | {or_rate:<12} | {ftr:<12}")

def main():
    stats_data = load_json(TEAM_STATS_FILE)
    if not stats_data:
        print("Stats data missing.")
        return

    metrics = get_simple_metrics(stats_data)
    
    bt_stats = load_json(BARTTORVIK_STATS_FILE)
    
    # Use current date in ET
    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    
    board = fetch_scoreboard(now.year, now.month, now.day)
    if not board or 'games' not in board or not board['games']:
        return

    # CSV Header
    header = ["Matchup", "Proj_Score_A", "Proj_Score_H", "Spread", "Conf_A", "Conf_H", 
              "AdjT_A", "AdjT_H", "AdjOE_A", "AdjOE_H", "AdjDE_A", "AdjDE_H", 
              "eFG_A", "eFG_H", "TO_A", "TO_H", "OR_A", "OR_H", "FTR_A", "FTR_H", "Market_Total"]
    
    import csv
    writer = csv.writer(sys.stdout)
    writer.writerow(header)
    
    for game_wrapper in board['games']:
        game = game_wrapper.get('game')
        if not game: continue
        
        away_raw = game['away']['names']['short']
        home_raw = game['home']['names']['short']
        
        nameA = find_team_in_dict(away_raw, metrics, BASKETBALL_ALIASES)
        nameH = find_team_in_dict(home_raw, metrics, BASKETBALL_ALIASES)

        if nameA and nameH:
            tA, tH = metrics[nameA], metrics[nameH]
            
            # Simple Math: Average of Team A Offense and Team B Defense
            scoreA = (tA['offense'] + tH['defense']) / 2
            scoreH = (tH['offense'] + tA['defense']) / 2
            
            match_str = f"{away_raw} @ {home_raw}"
            
            # Metadata Lookup
            btA_name = find_team_in_dict(away_raw, bt_stats, BASKETBALL_ALIASES)
            btH_name = find_team_in_dict(home_raw, bt_stats, BASKETBALL_ALIASES)
            btA = bt_stats.get(btA_name) if btA_name else None
            btH = bt_stats.get(btH_name) if btH_name else None
            
            # Helper to safely get value or N/A
            def get_val(data, key, default="N/A", precision=1):
                if not data: return default
                val = data.get(key)
                if val is None: return default
                try:
                    return round(float(val), precision)
                except:
                    return default

            # Row Data Construction
            row = [
                match_str,
                round(scoreA, 1),
                round(scoreH, 1),
                round(scoreH - scoreA, 1), # Spread
                btA['conf'] if (btA and 'conf' in btA) else 'N/A',
                btH['conf'] if (btH and 'conf' in btH) else 'N/A',
                get_val(btA, 'adj_t'),
                get_val(btH, 'adj_t'),
                get_val(btA, 'adj_off'),
                get_val(btH, 'adj_off'),
                get_val(btA, 'adj_def'),
                get_val(btH, 'adj_def'),
                get_val(btA, 'efg'),
                get_val(btH, 'efg_d'), # Use opponent defense stats for H? No, usually side-by-side means Team Stats
                # WAIT: User example "eFG_A, eFG_H". Usually compares the teams' own stats? 
                # Or Offense vs Defense? 
                # Context: "Tempo, Efficiency... All must be numeric only". 
                # Standard analysis lists Team A stats vs Team B stats.
                # Let's assume Team A's eFG% and Team B's eFG% (Offensive).
                # Re-reading: "AdjOE_A", "AdjOE_H". Yes, Team specific stats.
                get_val(btA, 'to'),
                get_val(btH, 'to'), # Team H Turnovers? Or Forced? "TO_H" usually means Team H's TO %.
                get_val(btA, 'or'),
                get_val(btH, 'or'),
                get_val(btA, 'ftr'),
                get_val(btH, 'ftr'),
                "N/A" # Market_Total
            ]
            
            # Correction: eFG_H in previous code used 'efg_d' (Defense) for H?
            # Previous Line 165: "round(btA['efg'], 1) ... / ... round(btH['efg_d'], 1)"
            # That was weird. Usually you compare A Off vs H Def. 
            # BUT the headers are "eFG_A", "eFG_H". This implies Team A's eFG and Team H's eFG. 
            # I will use 'efg' for both (Offensive eFG%).
            
            # Update row with correct keys
            row[12] = get_val(btA, 'efg')
            row[13] = get_val(btH, 'efg') # Fixed to use H's offensive eFG
            row[14] = get_val(btA, 'to')
            row[15] = get_val(btH, 'to')
            row[16] = get_val(btA, 'or')
            row[17] = get_val(btH, 'or')
            row[18] = get_val(btA, 'ftr')
            row[19] = get_val(btH, 'ftr')

            writer.writerow(row)

if __name__ == "__main__":
    main()
