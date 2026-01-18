import requests
import os
import json
from datetime import datetime

# The Odds API Configuration
# To use live data, set ODDS_API_KEY environment variable
API_KEY = os.getenv("ODDS_API_KEY", "YOUR_API_KEY_HERE")
BASE_URL = "https://api.the-odds-api.com/v4/sports"

# Local cache/fallback
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
MOCK_DATA_FILE = os.path.join(ROOT_DIR, "data", "mock_odds.json")

def get_odds(sport_key, regions='us', markets='totals'):
    """
    Fetches live totals for a given sport (nba, basketball_ncaa).
    """
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

def _get_mock_odds(sport_key):
    """
    Provides slightly randomized realistic odds for development when API key is missing.
    """
    # Seed with standard defaults if no file exists
    defaults = {
        'nba': 230.5,
        'ncaa': 145.5
    }
    
    # In a real scenario, we'd return a list of match-specific totals
    # For now, we return a simplified structure that mimic the API
    return [] # Returning empty to trigger fallback logic in populate scripts

def extract_total_for_matchup(odds_data, away_team, home_team):
    """
    Helper to find a specific game in the Odds API response.
    """
    for game in odds_data:
        # Check team name matches (could use mapping here)
        if (away_team in game['away_team'] or game['away_team'] in away_team) and \
           (home_team in game['home_team'] or game['home_team'] in home_team):
            
            # Extract first available total from bookmakers
            for bookmaker in game['bookmakers']:
                for market in bookmaker['markets']:
                    if market['key'] == 'totals':
                        return market['outcomes'][0]['point']
    return None

if __name__ == "__main__":
    # Test call
    import sys
    sport = "basketball_nba" if "nba" in sys.argv else "basketball_ncaa"
    print(f"Testing Odds Provider for {sport}...")
    data = get_odds(sport)
    print(f"Received {len(data)} games.")
