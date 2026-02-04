import os
import requests
import json
import sys
from datetime import datetime

# Add project root to sys.path for direct execution
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from utils.sportradar_provider import SportradarProvider

# The Odds API Configuration (Existing)
API_KEY = os.getenv("ODDS_API_KEY", "YOUR_API_KEY_HERE")
BASE_URL = "https://api.the-odds-api.com/v4/sports"

# Sportradar Configuration
sr_provider = SportradarProvider()

def get_odds(sport_key, regions='us', markets='totals', provider='render'):
    """
    Fetches live totals for a given sport.
    Priority: Render API -> Sportradar -> The Odds API
    """
    if provider == 'render':
        league = "ncaa" if "ncaa" in sport_key.lower() else "nba"
        url = f"https://ncaa-api-w2ry.onrender.com/stats/odds/{league}"
        print(f"Fetching centralized odds from {url}")
        try:
            from utils.ssl_adapter import get_robust_session
            session = get_robust_session(retries=2)
            
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                print(f"Standard fetch failed ({resp.status_code}). Retrying with SSL bypass...")
                resp = session.get(url, timeout=15, verify=False)

            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return data
            print(f"Centralized odds check returned {resp.status_code}. Falling back...")
            try:
                print(f"Error Details: {resp.text[:200]}")
            except: pass
        except Exception as e:
            print(f"Render Odds API failed ({e}). Falling back to Sportradar...")

    if provider == 'sportradar' or provider == 'render':
        return sr_provider.get_totals(sport_key)
    
    # Fallback to The Odds API
    if API_KEY == "YOUR_API_KEY_HERE" or not API_KEY:
        return _get_mock_odds(sport_key)

    params = {
        'api_key': API_KEY,
        'regions': regions,
        'markets': markets,
        'oddsFormat': 'decimal'
    }
    
    url = f"{BASE_URL}/{sport_key}/odds"
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Odds API Error: {response.status_code}")
            return _get_mock_odds(sport_key)
    except Exception as e:
        print(f"Request failed: {e}")
        return _get_mock_odds(sport_key)

def extract_total_for_matchup(odds_data, away_team, home_team, provider='render'):
    """
    Helper to find a specific game in the odds response.
    Supports Centralized Map, Sportradar, and The Odds API formats.
    """
    from utils.mapping import clean_team_name, BASKETBALL_ALIASES
    
    c_away = clean_team_name(away_team)
    c_home = clean_team_name(home_team)
    
    # Canonical mapping candidates
    def get_all_variants(name):
        c = clean_team_name(name)
        v = BASKETBALL_ALIASES.get(c, c)
        variants = {c, v}
        # Add all keys that map to the same canonical value
        for k, val in BASKETBALL_ALIASES.items():
            if val == v:
                variants.add(k)
        return variants

    variants_away = get_all_variants(away_team)
    variants_home = get_all_variants(home_team)

    def is_match(target_str):
        if not target_str: return False
        t_low = clean_team_name(target_str)
        away_match = any(v in t_low for v in variants_away)
        home_match = any(v in t_low for v in variants_home)
        return away_match and home_match

    # 1. Centralized Render API format (Dict: { "team a vs team b": total })
    if isinstance(odds_data, dict) and "sport_events" not in odds_data:
        for key, val in odds_data.items():
            if is_match(key):
                return val
        return None

    # 2. Sportradar format
    if isinstance(odds_data, dict) and "sport_events" in odds_data:
        events = odds_data.get("sport_events", [])
        for event in events:
            # Check competitor names
            comp_names = " ".join([c.get("name", "").lower() for c in event.get("competitors", [])])
            if is_match(comp_names):
                return sr_provider.extract_total(event)
        return None

    # 3. Original The Odds API logic
    if isinstance(odds_data, list):
        for game in odds_data:
            matchup_str = f"{game.get('away_team', '')} vs {game.get('home_team', '')}"
            if is_match(matchup_str):
                for bookmaker in game.get('bookmakers', []):
                    for market in bookmaker.get('markets', []):
                        if market['key'] == 'totals':
                            return market['outcomes'][0]['point']
    return None

def _get_mock_odds(sport_key):
    return []

if __name__ == "__main__":
    import sys
    sport = "nba" if "nba" in sys.argv else "ncaa"
    print(f"Testing Odds Provider (Centralized Path) for {sport}...")
    data = get_odds(sport, provider='render')
    print(f"Received data keys: {list(data.keys())[:5] if isinstance(data, dict) else 'list'}")
    
    # Test extraction
    test_away, test_home = "Lakers", "Celtics"
    total = extract_total_for_matchup(data, test_away, test_home)
    print(f"Extracted Total for {test_away}@{test_home}: {total}")
