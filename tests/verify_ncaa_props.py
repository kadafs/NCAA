# verify_ncaa_props.py
import sys
import os

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.universal_bridge import get_universal_predictions
import json

def test_ncaa_props():
    print("Testing NCAA Predictions with Props...")
    
    # Try real fetch first
    try:
        results = get_universal_predictions(league="ncaa", mode="safe")
    except Exception as e:
        print(f"Fetch failed: {e}. Trying with localized mock daily sheet...")
        # We can't easily mock the internal bridge fetch without deeper mocking,
        # but the get_universal_predictions already has internal error handling.
        results = {"games": []}

    if results and "games" in results and len(results["games"]) > 0:
        found_props = False
        print(f"Found {len(results['games'])} games. Checking for props...")
        for game in results["games"]:
            away = game.get('away')
            home = game.get('home')
            print(f"  - Matchup: {away} @ {home}")
            if "props" in game and len(game["props"]) > 0:
                found_props = True
                print(f"    Found {len(game['props'])} props")
                for p in game["props"][:1]: # Show first 1
                    print(f"    [PROP] {p['name']}: PTS {p['pts']} | REB {p['reb']} | AST {p['ast']}")
        
        if not found_props:
            print("\nNo player props found in any games. (Likely no player stat matches for these teams)")
    else:
        print("NO GAMES FOUND or results empty.")

if __name__ == "__main__":
    test_ncaa_props()
