import requests
import json
from utils.ssl_adapter import get_robust_session

def check_feb7_odds():
    url = "https://ncaa-api-w2ry.onrender.com/scoreboard/basketball-men/d1/2026/02/07"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    session = get_robust_session(retries=3)
    
    print(f"Checking {url}...")
    try:
        resp = session.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            games = data.get('games', [])
            print(f"Found {len(games)} games.")
            
            odds_found = 0
            for g_wrapper in games:
                g = g_wrapper.get('game', {})
                odds = g.get('odds', {})
                if 'total' in odds:
                    odds_found += 1
                
            print(f"Games with Odds: {odds_found}")
            if games:
                g0 = games[0].get('game', {})
                print(f"Sample: {g0.get('away', {}).get('names', {}).get('short')} @ {g0.get('home', {}).get('names', {}).get('short')} | Odds: {g0.get('odds')}")
        else:
            print(f"Failed with status: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_feb7_odds()
