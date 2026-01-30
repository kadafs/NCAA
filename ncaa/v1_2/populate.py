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
                        "away_seo": g.get('away', {}).get('names', {}).get('seo', ''),
                        "home_seo": g.get('home', {}).get('names', {}).get('seo', ''),
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

def load_market_csv(target_date_obj):
    """
    Looks for a file named data/ncaa_market_YYYY-MM-DD.csv.
    Returns a dictionary of {Home_Team_Name: Market_Total}.
    """
    import csv
    date_str = target_date_obj.strftime("%Y-%m-%d")
    filename = os.path.join(ROOT_DIR, "data", f"ncaa_market_{date_str}.csv")
    
    market_map = {}
    if not os.path.exists(filename):
        print(f"DEBUG: No market CSV found for {date_str}. Using safety defaults.")
        return market_map

    print(f"DEBUG: Found Market CSV for {date_str}. Injecting priorities...")
    try:
        # Load BT data to resolve names
        from ncaa.v1_2.populate import BARTTORVIK_FILE, BASKETBALL_ALIASES, find_team_in_dict, load_json
        bt_data = load_json(BARTTORVIK_FILE)
        
        with open(filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                matchup = row.get('Matchup', '')
                total_raw = row.get('Market_Odds') or row.get('Market Total')
                
                if not matchup or not total_raw:
                    continue
                
                import re
                total_match = re.search(r"(\d+\.?\d*)", str(total_raw))
                if not total_match:
                    continue
                total = float(total_match.group(1))

                # Identify teams in the CSV string
                temp_a, temp_b = None, None
                if ' vs ' in matchup:
                    parts = matchup.split(' vs ')
                    temp_a, temp_b = parts[0].strip(), parts[1].strip()
                elif '@' in matchup:
                    parts = matchup.split('@')
                    temp_a, temp_b = parts[0].strip(), parts[1].strip()
                
                if temp_a and temp_b:
                    # Resolve both to official names
                    team_a = find_team_in_dict(temp_a, bt_data, BASKETBALL_ALIASES)
                    team_b = find_team_in_dict(temp_b, bt_data, BASKETBALL_ALIASES)
                    
                    if team_a and team_b:
                        # Use frozenset for order-independent key
                        key = frozenset({team_a.lower(), team_b.lower()})
                        market_map[key] = total
        
        print(f"DEBUG: Successfully mapped {len(market_map)} market totals from CSV.")
        return market_map
    except Exception as e:
        print(f"ERROR: Failed to parse market CSV: {e}")
        return {}

def get_game_data(away_name, home_name, bt_data, score_data, market_total=145.5, away_seo="", home_seo=""):
    """Bridge raw stats to v1.2 Input Sheet columns. Fixed market propagation (V1.3)."""
    
    # 1. Resolve Teams
    teamA = find_team_in_dict(away_name, bt_data, BASKETBALL_ALIASES)
    teamH = find_team_in_dict(home_name, bt_data, BASKETBALL_ALIASES)
    
    if not teamA or not teamH: return None
    
    sA = bt_data[teamA]
    sH = bt_data[teamH]
    
    # 2. Extract PPG (from consolidated_stats.json)
    def find_ppg(team_name):
        for entry in score_data.get('scoring_offense', []):
            if entry['Team'] == team_name:
                return float(entry['PPG'])
        return (sA['adj_off'] * (sA['adj_t'] / 100)) if team_name == teamA else (sH['adj_off'] * (sH['adj_t'] / 100))

    ppgA = find_ppg(teamA)
    ppgH = find_ppg(teamH)
    
    # 3. Formulate Input Dictionary
    input_data = {
        "team": teamA,
        "opponent": teamH,
        "away_seo": away_seo,
        "home_seo": home_seo,
        "team_ppg": ppgA,
        "opp_ppg": ppgH,
        "market_total": market_total,
        "pace_adjustment": (sA['adj_t'] + sH['adj_t']) / 2,
        "efficiency_adjustment": (sA['adj_off'] + sH['adj_def'] + sH['adj_off'] + sA['adj_def']) / 4,
        "is_elite_offense": sA['adj_off'] > 115 or sH['adj_off'] > 115,
        "is_strong_defense": sA['adj_def'] < 100 or sH['adj_def'] < 100,
        "turnover_adjustment": (sA['to'] + sH['to']) / 2,
        "foul_adjustment": (sA['ftr'] + sH['ftr']) / 2,
        "conf": sA['conf']
    }
    
    return input_data

def get_daily_input_sheet(date_obj=None):
    from datetime import datetime
    import zoneinfo
    
    if date_obj is None:
        date_obj = datetime.now(zoneinfo.ZoneInfo("America/New_York"))

    bt = load_json(BARTTORVIK_FILE)
    sh = load_json(CONSOLIDATED_FILE)
    matchups = fetch_matchups(date_obj)
    
    # NEW: Load Market CSV for date-enforced overrides
    manual_market = load_market_csv(date_obj)
    
    # Fetch live odds fallback
    odds_data = get_odds("basketball_ncaa")
    
    daily_sheet = []
    for m in matchups:
        # Priority 1: Manual CSV Injection
        # Priority 2: Real-time Odds API
        # Priority 3: Scoreboard Data
        # Priority 4: Demo Fallback (145.5)
        
        # Resolve scoreboard name to official key first
        home_clean = m['home']
        away_clean = m['away']
        
        resolved_home = find_team_in_dict(home_clean, bt, BASKETBALL_ALIASES)
        resolved_away = find_team_in_dict(away_clean, bt, BASKETBALL_ALIASES)
        
        h_key = resolved_home.lower() if resolved_home else home_clean.lower()
        a_key = resolved_away.lower() if resolved_away else away_clean.lower()
        
        lookup_key = frozenset({h_key, a_key})

        if lookup_key in manual_market:
            market_total = manual_market[lookup_key]
            source = "Manual CSV Injection"
        else:
            live_total = extract_total_for_matchup(odds_data, m['away'], m['home'])
            market_total = live_total if live_total else m.get('total', 145.5)
            source = "API/Scoreboard"
        
        data = get_game_data(m['away'], m['home'], bt, sh, market_total, m.get('away_seo'), m.get('home_seo'))
        if data:
            data['market_source'] = source
            daily_sheet.append(data)
            
    return daily_sheet
