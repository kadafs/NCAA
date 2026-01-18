# EuroLeague PPG+PED Hybrid Totals v1.2 Data Population Layer
import json
import os
import sys
from datetime import datetime
import zoneinfo

# Add root for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from utils.mapping import find_team_in_dict, EURO_TRICODES

# Base paths relative to Project Root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

EURO_STATS_FILE = os.path.join(ROOT_DIR, "data", "euro_stats.json")
EURO_MATCHUPS_FILE = os.path.join(ROOT_DIR, "data", "euro_matchups.json")
# EuroLeague injuries are less centralized, but we can add a placeholder
EURO_INJURY_FILE = os.path.join(ROOT_DIR, "data", "euro_injury_notes.json")

def load_json(path):
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}

def get_euro_game_data(matchup, all_stats, injury_notes):
    """Bridge EuroLeague data to v1.2 Input Sheet columns."""
    # 1. Resolve stats
    away_team = find_team_in_dict(matchup['away'], all_stats)
    home_team = find_team_in_dict(matchup['home'], all_stats)
    
    if not away_team or not home_team: return None
    
    statsA = all_stats.get(away_team, {})
    statsH = all_stats.get(home_team, {})
    
    # 2. Extract Metrics
    input_data = {
        "team": away_team,
        "opponent": home_team,
        "team_ppg": statsA.get('pts', 80.0),
        "opp_ppg": statsH.get('pts', 80.0),
        "market_total": matchup.get('total', 160.0), 
        "pace_adjustment": (statsA.get('adj_t', 72.0) + statsH.get('adj_t', 72.0)) / 2,
        "efficiency_adjustment": (
            statsA.get('adj_off', 110.0) + statsH.get('adj_def', 110.0) +
            statsH.get('adj_off', 110.0) + statsA.get('adj_def', 110.0)
        ) / 4,
        "three_pa_total": statsA.get('fg3a', 25.0) + statsH.get('fg3a', 25.0),
        "is_b2b_team": False, # Placeholder
        "is_b2b_opp": False,
        "is_b2b_both": False
    }
    
    return input_data

def get_euro_daily_input_sheet():
    stats = load_json(EURO_STATS_FILE)
    matchups = load_json(EURO_MATCHUPS_FILE)
    injuries = load_json(EURO_INJURY_FILE)
    
    # Live odds for EuroLeague often requires a different sport key
    # But for now we'll use matchups.json as the source of truth
    
    daily_sheet = []
    for m in matchups:
        data = get_euro_game_data(m, stats, injuries)
        if data:
            daily_sheet.append(data)
            
    return daily_sheet
