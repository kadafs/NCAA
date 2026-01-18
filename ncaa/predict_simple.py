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
    if bt_stats:
        print(f"Loaded {len(bt_stats)} teams from BartTorvik for advanced metrics.")
    
    injury_notes = load_json(INJURY_NOTES_FILE)
    if injury_notes:
        print(f"Loaded injury notes for {len(injury_notes)} teams.")

    
    # Use current date in ET
    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    print(f"\n--- Simple Predictions for {now.strftime('%Y-%m-%d')} ---")
    print("(Based ONLY on PPG and OPP PPG averages)")
    
    board = fetch_scoreboard(now.year, now.month, now.day)
    if not board or 'games' not in board or not board['games']:
        print("No games found on scoreboard.")
        return

    # Updated Header for v1.8 Intelligence (Split OE/DE)
    header = f"{'Matchup':<35} | {'Proj Score':<15} | {'Spread':<8} | {'Conf (A/H)':<10} | {'Adj T(A/H)':<11} | {'AdjOE(A/H)':<12} | {'AdjDE(A/H)':<12} | {'eFG% (A/H)':<12} | {'TO% (A/H)':<12} | {'OR% (A/H)':<12} | {'FTR (A/H)':<12}"
    print(header)
    print("-" * len(header))
    
    game_notes = []
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
            score_str = f"{scoreA:.1f} - {scoreH:.1f}"
            spread_str = f"{scoreH - scoreA:+.1f}"
            
            # Metadata Lookup
            btA_name = find_team_in_dict(away_raw, bt_stats, BASKETBALL_ALIASES)
            btH_name = find_team_in_dict(home_raw, bt_stats, BASKETBALL_ALIASES)
            btA = bt_stats.get(btA_name) if btA_name else None
            btH = bt_stats.get(btH_name) if btH_name else None
            
            conf_str = f"{btA['conf'] if (btA and 'conf' in btA) else 'N/A'}/{btH['conf'] if (btH and 'conf' in btH) else 'N/A'}"
            t_str = f"{round(btA['adj_t'], 1) if btA else 'N/A'}/{round(btH['adj_t'], 1) if btH else 'N/A'}"
            
            # Separate AdjOE and AdjDE
            oe_str = f"{round(btA['adj_off'], 1) if btA else 'N/A'}/{round(btH['adj_off'], 1) if btH else 'N/A'}"
            de_str = f"{round(btA['adj_def'], 1) if btA else 'N/A'}/{round(btH['adj_def'], 1) if btH else 'N/A'}"
            
            # Use 0 check for Four Factors
            efg_str = f"{round(btA['efg'], 1) if (btA and btA.get('efg')) else 'N/A'}/{round(btH['efg_d'], 1) if (btH and btH.get('efg_d')) else 'N/A'}"
            to_str = f"{round(btA['to'], 1) if (btA and btA.get('to')) else 'N/A'}/{round(btH['to_d'], 1) if (btH and btH.get('to_d')) else 'N/A'}"
            or_str = f"{round(btA['or'], 1) if (btA and btA.get('or')) else 'N/A'}/{round(btH['or_d'], 1) if (btH and btH.get('or_d')) else 'N/A'}"
            ftr_str = f"{round(btA['ftr'], 1) if (btA and btA.get('ftr')) else 'N/A'}/{round(btH['ftr_d'], 1) if (btH and btH.get('ftr_d')) else 'N/A'}"
            
            # Custom print for split columns
            print(f"{match_str:<35} | {score_str:<15} | {spread_str:<8} | {conf_str:<10} | {t_str:<11} | {oe_str:<12} | {de_str:<12} | {efg_str:<12} | {to_str:<12} | {or_str:<12} | {ftr_str:<12}")

            # Injury Notes
            injA_name = find_injury_team(away_raw, injury_notes)
            injH_name = find_injury_team(home_raw, injury_notes)
            
            notes = []
            if injA_name and injury_notes[injA_name]:
                for item in injury_notes[injA_name]:
                    notes.append(f"  [A] {item['player']} ({item['status']}): {item['note']}")
            if injH_name and injury_notes[injH_name]:
                for item in injury_notes[injH_name]:
                    notes.append(f"  [H] {item['player']} ({item['status']}): {item['note']}")
            
            if notes:
                game_notes.append((match_str, notes))

    if game_notes:
        print("\n" + "="*50)
        print("SITUATIONAL NOTES (Injuries, Travel, etc.)")
        print("="*50)
        for matchup, notes in game_notes:
            print(f"\n{matchup}:")
            for n in notes:
                print(n)

if __name__ == "__main__":
    main()
