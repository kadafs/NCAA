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
    # Resolve stats using robust mapping
    away_team = find_team_in_dict(matchup['away'], all_stats, BASKETBALL_ALIASES)
    home_team = find_team_in_dict(matchup['home'], all_stats, BASKETBALL_ALIASES)
    
    if not away_team or not home_team: return None
    
    statsA = all_stats.get(away_team)
    statsH = all_stats.get(home_team)
    
    # Heuristic for B2B based on game count in notes or schedule (limited in current fetchers)
    def check_b2b(tn):
        notes = injury_notes.get(tn, [])
        for n in notes:
            if "back to back" in n.get('note', '').lower(): return True
        return False

    is_b2bA = check_b2b(away_team)
    is_b2bH = check_b2b(home_team)
    
    input_data = {
        "team": away_team,
        "opponent": home_team,
        "team_ppg": statsA.get('pts', 115.0),
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

def load_nba_market_csv(target_date_obj):
    """
    Looks for a file named data/nba_market_YYYY-MM-DD.csv.
    Returns a dictionary of {frozenset({away, home}): Market_Total}.
    """
    import csv
    import re
    date_str = target_date_obj.strftime("%Y-%m-%d")
    filename = os.path.join(ROOT_DIR, "data", f"nba_market_{date_str}.csv")
    
    market_map = {}
    if not os.path.exists(filename):
        return market_map

    print(f"DEBUG: Found NBA Market CSV for {date_str}. Injecting priorities...")
    try:
        stats = load_json(NBA_STATS_FILE)
        with open(filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                matchup = row.get('Matchup', '')
                total_raw = row.get('Market_Odds') or row.get('Market Total')
                
                if not matchup or not total_raw: continue
                
                total_match = re.search(r"(\d+\.?\d*)", str(total_raw))
                if not total_match: continue
                total = float(total_match.group(1))

                temp_a, temp_b = None, None
                if ' vs ' in matchup:
                    parts = matchup.split(' vs ')
                    temp_a, temp_b = parts[0].strip(), parts[1].strip()
                elif '@' in matchup:
                    parts = matchup.split('@')
                    temp_a, temp_b = parts[0].strip(), parts[1].strip()
                
                if temp_a and temp_b:
                    team_a = find_team_in_dict(temp_a, stats, BASKETBALL_ALIASES)
                    team_b = find_team_in_dict(temp_b, stats, BASKETBALL_ALIASES)
                    if team_a and team_b:
                        key = frozenset({team_a.lower(), team_b.lower()})
                        market_map[key] = total
        
        print(f"DEBUG: Successfully mapped {len(market_map)} NBA market totals from CSV.")
        return market_map
    except Exception as e:
        print(f"ERROR: Failed to parse NBA market CSV: {e}")
        return {}

def get_nba_daily_input_sheet(date_obj=None):
    if date_obj is None:
        date_obj = datetime.now(zoneinfo.ZoneInfo("America/New_York"))

    stats = load_json(NBA_STATS_FILE)
    matchups = load_json(NBA_MATCHUPS_FILE)
    injuries = load_json(NBA_INJURY_FILE)
    manual_market = load_nba_market_csv(date_obj)
    
    # Fetch live odds fallback
    odds_data = get_odds("basketball_nba")
    
    daily_sheet = []
    for m in matchups:
        # Priority 1: Manual CSV
        # Priority 2: API
        # Priority 3: Matchup Default
        
        # Resolve names for lookup
        res_away = find_team_in_dict(m['away'], stats, BASKETBALL_ALIASES)
        res_home = find_team_in_dict(m['home'], stats, BASKETBALL_ALIASES)
        
        lookup_key = None
        if res_away and res_home:
            lookup_key = frozenset({res_away.lower(), res_home.lower()})

        if lookup_key and lookup_key in manual_market:
            market_total = manual_market[lookup_key]
            source = "Manual CSV Injection"
        else:
            live_total = extract_total_for_matchup(odds_data, m['away'], m['home'])
            market_total = live_total if live_total else m.get('total', 230.5)
            source = "API/Matchup"
        
        m['total'] = market_total
        data = get_nba_game_data(m, stats, injuries)
        if data:
            data['market_source'] = source
            daily_sheet.append(data)
            
    return daily_sheet
