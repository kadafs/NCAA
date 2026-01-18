# NBA PPG+PED Hybrid Totals v1.2 Data Population Layer
import json
import os
import sys
from datetime import datetime
import zoneinfo

# Add root for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES, NBA_TRICODES
from utils.odds_provider import get_odds, extract_total_for_matchup

# Base paths relative to Project Root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

NBA_STATS_FILE = os.path.join(ROOT_DIR, "data", "nba_stats.json")
NBA_MATCHUPS_FILE = os.path.join(ROOT_DIR, "data", "nba_matchups.json")
NBA_INJURY_FILE = os.path.join(ROOT_DIR, "data", "nba_injury_notes.json")

def load_json(path):
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_nba_game_data(matchup, all_stats, injury_notes):
    """Bridge nba_api data to v1.2 Input Sheet columns."""
    # 1. Resolve stats using robust mapping
    away_team = find_team_in_dict(matchup['away'], all_stats, BASKETBALL_ALIASES)
    home_team = find_team_in_dict(matchup['home'], all_stats, BASKETBALL_ALIASES)
    
    if not away_team or not home_team: return None
    
    statsA = all_stats.get(away_team)
    statsH = all_stats.get(home_team)
    
    # 2. Extract Metrics
    # Note: nba_api stats vary; assuming standard 'PTS', 'PACE', 'OFF_RATING', 'DEF_RATING' keys
    # and situational flags like B2B (optional for now, can be manual via notes)
    
    # Heuristic for B2B based on game count in notes or schedule (limited in current fetchers)
    # We'll default to False unless we find specific "B2B" strings in injury notes
    def check_b2b(tn):
        notes = injury_notes.get(tn, [])
        for n in notes:
            if "back to back" in n.get('note', '').lower(): return True
        return False

    is_b2bA = check_b2b(away_team)
    is_b2bH = check_b2b(home_team)
    
    # 2. Extract Metrics using correct keys
    input_data = {
        "team": away_team,
        "opponent": home_team,
        "team_ppg": statsA.get('pts', 115.0), # Fallback if pts not present
        "opp_ppg": statsH.get('pts', 115.0),
        "market_total": matchup.get('total', 230.5), 
        "pace_adjustment": (statsA.get('adj_t', 100.0) + statsH.get('adj_t', 100.0)) / 2,
        "efficiency_adjustment": (
            statsA.get('adj_off', 115.0) + statsH.get('adj_def', 115.0) +
            statsH.get('adj_off', 115.0) + statsA.get('adj_def', 115.0)
        ) / 4,
        "three_pa_total": statsA.get('fg3a', 35.0) + statsH.get('fg3a', 35.0),
        "is_b2b_team": is_b2bA,
        "is_b2b_opp": is_b2bH,
        "is_b2b_both": is_b2bA and is_b2bH
    }
    
    return input_data

def get_nba_daily_input_sheet():
    stats = load_json(NBA_STATS_FILE)
    matchups = load_json(NBA_MATCHUPS_FILE)
    injuries = load_json(NBA_INJURY_FILE)
    
    # Fetch live odds
    odds_data = get_odds("basketball_nba")
    
    daily_sheet = []
    for m in matchups:
        # Try to find a live total for this matchup
        live_total = extract_total_for_matchup(odds_data, m['away'], m['home'])
        # If no live total found, use the default from the matchup (if any)
        market_total = live_total if live_total else m.get('total', 230.5)
        
        # Override the total in the matchup dict so get_nba_game_data picks it up
        m['total'] = market_total
        
        data = get_nba_game_data(m, stats, injuries)
        if data:
            daily_sheet.append(data)
            
    return daily_sheet
