import os
import sys
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from utils.odds_provider import get_odds, extract_total_for_matchup

def debug_specific_odds():
    print("Fetching live NCAA odds from Render...")
    odds_data = get_odds("ncaa", provider='render')
    
    if not odds_data:
        print("Failed to fetch odds data.")
        return

    print(f"Total games in odds: {len(odds_data)}")
    
    matchups_to_check = [
        ("Virginia Tech", "N.C. State"),
        ("Cleveland St.", "IU Indy"),
        ("North Florida", "Queens (NC)"),
        ("Oral Roberts", "St. Thomas (MN)"),
        ("UT Arlington", "Utah Valley")
    ]
    
    print("\nResults:")
    for away, home in matchups_to_check:
        total = extract_total_for_matchup(odds_data, away, home)
        print(f"[{away} @ {home}] -> Total: {total}")

if __name__ == "__main__":
    debug_specific_odds()
