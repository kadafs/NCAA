# NCAA PPG+PED Hybrid Totals v1.2 Data Population Layer
import json
import os
import requests
import sys

# Add parent and root for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES

BARTTORVIK_FILE = "data/barttorvik_stats.json"
CONSOLIDATED_FILE = "data/consolidated_stats.json"
INJURY_FILE = "data/injury_notes.json"

def load_json(path):
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_matchups():
    """Fetch today's D1 matchups from the scoreboard endpoint."""
    from datetime import datetime
    import zoneinfo
    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    url = f"https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/{now.year}/{now.month:02d}/{now.day:02d}"
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            games = []
            for g_wrapper in data.get('games', []):
                g = g_wrapper.get('game')
                if not g: continue
                games.append({
                    "away": g['away']['names']['short'],
                    "home": g['home']['names']['short'],
                    # Scoreboard might have totals in odds section
                    "total": g.get('odds', {}).get('total', 145.5) # Default/Example
                })
            return games
    except Exception as e:
        print(f"Error fetching matchups: {e}")
    return []

def get_game_data(away_name, home_name, bt_data, score_data, market_total=0):
    """Bridge raw stats to v1.2 Input Sheet columns."""
    
    # 1. Resolve Teams
    teamA = find_team_in_dict(away_name, bt_data, BASKETBALL_ALIASES)
    teamH = find_team_in_dict(home_name, bt_data, BASKETBALL_ALIASES)
    
    if not teamA or not teamH: return None
    
    sA = bt_data[teamA]
    sH = bt_data[teamH]
    
    # 2. Extract PPG (from consolidated_stats.json)
    # We need to find the team in the 'scoring_offense' list
    def find_ppg(team_name):
        for entry in score_data.get('scoring_offense', []):
            if entry['Team'] == team_name:
                return float(entry['PPG'])
        # Fallback to BartTorvik estimate if not found
        return (sA['adj_off'] * (sA['adj_t'] / 100)) if team_name == teamA else (sH['adj_off'] * (sH['adj_t'] / 100))

    ppgA = find_ppg(teamA)
    ppgH = find_ppg(teamH)
    
    # 3. Formulate Input Dictionary
    input_data = {
        "team": teamA,
        "opponent": teamH,
        "team_ppg": ppgA,
        "opp_ppg": ppgH,
        "market_total": market_total,
        "pace_adjustment": (sA['adj_t'] + sH['adj_t']) / 2, # Mean pace
        "efficiency_adjustment": (sA['adj_off'] + sH['adj_def'] + sH['adj_off'] + sA['adj_def']) / 4,
        "is_elite_offense": sA['adj_off'] > 115 or sH['adj_off'] > 115,
        "is_strong_defense": sA['adj_def'] < 100 or sH['adj_def'] < 100,
        "turnover_adjustment": (sA['to'] + sH['to']) / 2,
        "foul_adjustment": (sA['ftr'] + sH['ftr']) / 2,
        "conf": sA['conf'] # Use away team conf as proxy or create composite
    }
    
    return input_data

def get_daily_input_sheet():
    bt = load_json(BARTTORVIK_FILE)
    sh = load_json(CONSOLIDATED_FILE)
    matchups = fetch_matchups()
    
    daily_sheet = []
    for m in matchups:
        data = get_game_data(m['away'], m['home'], bt, sh, m['total'])
        if data:
            daily_sheet.append(data)
            
    return daily_sheet
