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

def debug_failures():
    # 1. Fetch Odds
    print("Fetching Odds...")
    url_odds = "https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa"
    try:
        resp = requests.get(url_odds, verify=False, timeout=15)
        odds_data = resp.json()
        print(f"Total Odds Keys: {len(odds_data)}")
    except Exception as e:
        print(f"Failed to fetch odds: {e}")
        return

    # 2. Fetch Scoreboard (Feb 9)
    print("Fetching Scoreboard for Feb 9...")
    url_sb = "https://ncaa-api-w2ry.onrender.com/scoreboard/basketball-men/d1/2026/02/09"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url_sb, headers=headers, verify=False, timeout=15)
        if resp.status_code != 200:
            print(f"SB Failed: {resp.status_code}")
            return
        sb_data = resp.json()
    except Exception as e:
        print(f"Failed to fetch scoreboard: {e}")
        return

    # 3. Load BartTorvik for canonical name lookup
    bt_data = {}
    bt_path = "data/barttorvik_stats.json"
    if os.path.exists(bt_path):
        with open(bt_path, "r") as f:
            bt_data = json.load(f)

    print("\n--- DETAILED MATCHING ANALYSIS ---")
    for g_wrapper in sb_data.get('games', []):
        g = g_wrapper.get('game')
        if not g: continue
        away = g.get('away', {}).get('names', {}).get('short', 'AWY')
        home = g.get('home', {}).get('names', {}).get('short', 'HME')
        sb_total = g.get('odds', {}).get('total')
        
        extracted = extract_total_for_matchup(odds_data, away, home)
        
        if not extracted:
            print(f"FAILURE: {away} vs {home}")
            print(f"  Clean Away: {clean_team_name(away)}")
            print(f"  Clean Home: {clean_team_name(home)}")
            
            # Find in BT
            resolved_away = find_team_in_dict(away, bt_data, BASKETBALL_ALIASES)
            resolved_home = find_team_in_dict(home, bt_data, BASKETBALL_ALIASES)
            print(f"  Resolved Away (BT): {resolved_away}")
            print(f"  Resolved Home (BT): {resolved_home}")
            
            # Show similar keys in odds_data
            c_away = clean_team_name(away)
            c_home = clean_team_name(home)
            for k in odds_data.keys():
                if c_away in k or c_home in k:
                    print(f"  Similar Key in Odds: '{k}'")
        else:
            print(f"SUCCESS: {away} vs {home} -> {extracted}")

if __name__ == "__main__":
    debug_failures()
