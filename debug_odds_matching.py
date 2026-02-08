import os
import sys

# Add root for core imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.odds_provider import extract_total_for_matchup

def debug_matching():
    # Simulated odds data from Render
    odds_data = {
        "nebraska cornhuskers vs rutgers scarlet knights": 133.5,
        "ole miss rebels vs texas longhorns": 150.5,
        "nicholls state colonels vs texas a&m-cc islanders": 140.0
    }
    
    test_cases = [
        ("Nebraska", "Rutgers"),
        ("Mississippi", "Texas"),
        ("USC", "Nicholls St.")
    ]
    
    for away, home in test_cases:
        total = extract_total_for_matchup(odds_data, away, home)
        print(f"Matchup: {away} @ {home} -> Extracted Total: {total}")

if __name__ == "__main__":
    debug_matching()
