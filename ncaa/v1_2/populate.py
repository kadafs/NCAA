# NCAA PPG+PED Hybrid Totals v1.2 Data Population Layer
import json
import os
import requests
import sys

# Add parent and root for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES
from utils.odds_provider import get_odds, extract_total_for_matchup

# Base paths relative to Project Root
# This script is in ncaa/v1_2/ (2 levels deep)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

BARTTORVIK_FILE = os.path.join(ROOT_DIR, "data", "barttorvik_stats.json")
CONSOLIDATED_FILE = os.path.join(ROOT_DIR, "data", "consolidated_stats.json")
INJURY_FILE = os.path.join(ROOT_DIR, "data", "injury_notes.json")

def load_json(path):
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_matchups(date_obj=None):
    """Fetch D1 matchups for a specific date from the scoreboard endpoint."""
    from datetime import datetime
    import zoneinfo
    
    if date_obj is None:
        date_obj = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
        
    year = date_obj.year
    month = date_obj.month
    day = date_obj.day
    
    # Try local ports first, then external
    sources = [
        f"http://localhost:3005/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}",
        f"http://localhost:3000/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}",
        f"https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    for url in sources:
        try:
            print(f"DEBUG: Fetching NCAA matchups from: {url}")
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                games = []
                for g_wrapper in data.get('games', []):
                    g = g_wrapper.get('game')
                    if not g: continue
                    games.append({
                        "away": g.get('away', {}).get('names', {}).get('short', 'AWY'),
                        "home": g.get('home', {}).get('names', {}).get('short', 'HME'),
                        "total": g.get('odds', {}).get('total', 145.5)
                    })
                if games:
                    print(f"DEBUG: Successfully fetched {len(games)} games from {url}")
                    return games
                else:
                    print(f"DEBUG: URL {url} returned successful status but 0 games.")
            else:
                print(f"DEBUG: Failed to fetch from {url} (Status: {resp.status_code})")
        except Exception as e:
            print(f"DEBUG: Error fetching from {url}: {e}")
            continue
            
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

def get_daily_input_sheet(date_obj=None):
    bt = load_json(BARTTORVIK_FILE)
    sh = load_json(CONSOLIDATED_FILE)
    matchups = fetch_matchups(date_obj)
    
    # Fetch live odds (Note: get_odds might need date support too if Odds API supports it, but for now we fallback)
    odds_data = get_odds("basketball_ncaa")
    
    daily_sheet = []
    for m in matchups:
        # Try to find a live total for this matchup
        live_total = extract_total_for_matchup(odds_data, m['away'], m['home'])
        market_total = live_total if live_total else m['total']
        
        data = get_game_data(m['away'], m['home'], bt, sh, market_total)
        if data:
            daily_sheet.append(data)
            
    return daily_sheet
