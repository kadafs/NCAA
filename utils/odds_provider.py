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

def get_odds(sport_key, regions='us', markets='totals', provider='sportradar'):
    """
    Fetches live totals for a given sport.
    Defaulting to sportradar for new implementation.
    """
    if provider == 'sportradar':
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

def extract_total_for_matchup(odds_data, away_team, home_team, provider='sportradar'):
    """
    Helper to find a specific game in the odds response.
    """
    if provider == 'sportradar':
        # odds_data is the full sportradar response
        events = odds_data.get("sport_events", [])
        for event in events:
            # Simple name match (Sportradar uses full names)
            names = [c.get("name", "").lower() for c in event.get("competitors", [])]
            if away_team.lower() in str(names) or home_team.lower() in str(names):
                return sr_provider.extract_total(event)
        return None

    # Original Odds API logic
    for game in odds_data:
        if (away_team in game['away_team'] or game['away_team'] in away_team) and \
           (home_team in game['home_team'] or game['home_team'] in home_team):
            
            for bookmaker in game['bookmakers']:
                for market in bookmaker['markets']:
                    if market['key'] == 'totals':
                        return market['outcomes'][0]['point']
    return None

def _get_mock_odds(sport_key):
    # (Existing mock function remains same for backend compatibility)
    return []

if __name__ == "__main__":
    import sys
    sport = "nba" if "nba" in sys.argv else "ncaa"
    print(f"Testing Odds Provider (Sportradar Mock) for {sport}...")
    data = get_odds(sport, provider='sportradar')
    print(f"Received {len(data.get('sport_events', []))} events.")
    if data.get('sport_events'):
        total = extract_total_for_matchup(data, "Away", "Home")
        print(f"Extracted Total: {total}")
