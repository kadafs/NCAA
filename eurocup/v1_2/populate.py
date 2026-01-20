import json
import os
import sys

# Add root for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES

# Base paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
DATA_DIR = os.path.join(ROOT_DIR, "data")

STATS_FILE = os.path.join(DATA_DIR, "eurocup_stats.json")
MATCHUPS_FILE = os.path.join(DATA_DIR, "eurocup_matchups.json")
INJURY_NOTES_FILE = os.path.join(DATA_DIR, "eurocup_injury_notes.json")

def load_json(path):
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return None

def get_eurocup_game_data():
    """
    Standardizes EuroCup data for the Universal Basketball Engine.
    """
    stats = load_json(STATS_FILE)
    matchups = load_json(MATCHUPS_FILE)
    injuries = load_json(INJURY_NOTES_FILE) or {}

    if not stats or not matchups:
        print("Missing EuroCup stats or matchups.")
        return []

    input_sheet = []
    
    for m in matchups:
        away_raw = m['away']
        home_raw = m['home']
        
        nameA = find_team_in_dict(away_raw, stats, BASKETBALL_ALIASES)
        nameH = find_team_in_dict(home_raw, stats, BASKETBALL_ALIASES)
        
        if nameA and nameH:
            sA = stats[nameA]
            sH = stats[nameH]
            
            matchup_data = {
                "away": nameA,
                "home": nameH,
                "away_stats": sA,
                "home_stats": sH,
                "away_injuries": injuries.get(nameA, []),
                "home_injuries": injuries.get(nameH, []),
                "market_total": m.get('total', 165.0),
                "is_b2b_away": False, # EuroCup schedule usually weekly
                "is_b2b_home": False,
                "travel_distance": 0 # Placeholder
            }
            input_sheet.append(matchup_data)
            
    return input_sheet

if __name__ == "__main__":
    data = get_eurocup_game_data()
    print(f"Populated {len(data)} EuroCup matchups for the engine.")
