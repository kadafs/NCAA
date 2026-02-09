import requests
import json
import os
import sys

# Add root to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from utils.ssl_adapter import get_robust_session

def list_games(date_str):
    session = get_robust_session(retries=3)
    url = f"https://ncaa-api-w2ry.onrender.com/scoreboard/basketball-men/d1/{date_str.replace('-', '/')}"
    print(f"Fetching: {url}")
    try:
        resp = session.get(url, timeout=20)
        if resp.status_code != 200:
            resp = session.get(url, timeout=20, verify=False)
        data = resp.json()
        print(f"Total Games in JSON: {len(data.get('games', []))}")
        for g_wrapper in data.get('games', []):
            g = g_wrapper.get('game')
            if not g: continue
            away = g.get('away', {}).get('names', {}).get('short', 'AWY')
            home = g.get('home', {}).get('names', {}).get('short', 'HME')
            print(f"- {away} at {home}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else "2026-02-09"
    list_games(date)
