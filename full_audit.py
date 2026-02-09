import requests
import json
import os
import sys

# Add root to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from utils.odds_provider import extract_total_for_matchup
from utils.mapping import clean_team_name, find_team_in_dict, BASKETBALL_ALIASES

def full_audit():
    headers = {"User-Agent": "Mozilla/5.0"}
    from utils.ssl_adapter import get_robust_session
    session = get_robust_session(retries=3)
    
    # 1. Fetch Scoreboard Feb 9
    url_sb = "https://ncaa-api-w2ry.onrender.com/scoreboard/basketball-men/d1/2026/02/09"
    print(f"Fetching Scoreboard: {url_sb}")
    try:
        resp = session.get(url_sb, headers=headers, timeout=20)
        if resp.status_code != 200:
            resp = session.get(url_sb, headers=headers, timeout=20, verify=False)
        sb_data = resp.json()
        games = sb_data.get('games', [])
        print(f"Games Found: {len(games)}")
    except Exception as e:
        print(f"SB Fetch Failed: {e}")
        return

    # 2. Fetch Odds
    url_odds = "https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa"
    print(f"Fetching Odds: {url_odds}")
    try:
        resp = session.get(url_odds, timeout=20)
        if resp.status_code != 200:
            resp = session.get(url_odds, timeout=20, verify=False)
        odds_data = resp.json()
        print(f"Odds Keys: {len(odds_data)}")
    except Exception as e:
        print(f"Odds Fetch Failed: {e}")
        return

    bt_data = {}
    bt_path = "data/barttorvik_stats.json"
    if os.path.exists(bt_path):
        with open(bt_path, "r") as f:
            bt_data = json.load(f)

    print("\n--- FULL AUDIT ---")
    for g_wrapper in games:
        g = g_wrapper.get('game')
        if not g: continue
        away = g.get('away', {}).get('names', {}).get('short', 'AWY')
        home = g.get('home', {}).get('names', {}).get('short', 'HME')
        
        extracted = extract_total_for_matchup(odds_data, away, home)
        status = "OK" if extracted else "MISSING"
        print(f"{status}: {away} at {home} -> {extracted}")
        
        if not extracted:
            # Check substrings
            c_away = clean_team_name(away)
            c_home = clean_team_name(home)
            matches = [k for k in odds_data.keys() if c_away in k or c_home in k]
            if matches:
                print(f"  Partial Odds Keys: {matches}")
            
            # Resolved
            res_a = find_team_in_dict(away, bt_data, BASKETBALL_ALIASES)
            res_h = find_team_in_dict(home, bt_data, BASKETBALL_ALIASES)
            print(f"  Resolved: {res_a} at {res_h}")

if __name__ == "__main__":
    full_audit()
