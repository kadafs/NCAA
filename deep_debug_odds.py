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

def deep_debug():
    from utils.ssl_adapter import get_robust_session
    session = get_robust_session(retries=3)
    
    # Fetch Data
    url_sb = "https://ncaa-api-w2ry.onrender.com/scoreboard/basketball-men/d1/2026/02/09"
    url_odds = "https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa"
    
    try:
        sb_data = session.get(url_sb, verify=False, timeout=20).json()
        odds_data = session.get(url_odds, verify=False, timeout=20).json()
    except Exception as e:
        print(f"Fetch Failed: {e}")
        return

    targets = [
        ("Xavier", "St. John's (NY)"),
        ("Saint Francis", "Chicago St."),
        ("Jackson St.", "Ark.-Pine Bluff"),
        ("Northwestern St.", "Lamar University"),
        ("Central Ark.", "North Ala.")
    ]

    print("\n--- DEEP DEBUG ---")
    
    # Re-implement get_all_variants for visibility
    def get_all_variants(name):
        c = clean_team_name(name)
        v = BASKETBALL_ALIASES.get(c, c)
        variants = {c, v}
        for k, val in BASKETBALL_ALIASES.items():
            if val == v:
                variants.add(k)
        return variants

    for away_sb, home_sb in targets:
        print(f"\nMatchup: {away_sb} at {home_sb}")
        v_away = get_all_variants(away_sb)
        v_home = get_all_variants(home_sb)
        print(f"  Away Variants: {v_away}")
        print(f"  Home Variants: {v_home}")
        
        found = False
        for key, val in odds_data.items():
            t_low = clean_team_name(key)
            away_match = any(v in t_low for v in v_away)
            home_match = any(v in t_low for v in v_home)
            if away_match and home_match:
                print(f"  MATCH FOUND! Key: '{key}' Total: {val}")
                found = True
            elif away_match:
                # Potential partial match
                print(f"  Away matched but home failed: '{key}' (Clean: {t_low})")
            elif home_match:
                print(f"  Home matched but away failed: '{key}' (Clean: {t_low})")
        
        if not found:
            print("  NO MATCH FOUND.")

if __name__ == "__main__":
    deep_debug()
