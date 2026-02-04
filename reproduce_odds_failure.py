# reproduce_odds_failure.py
import sys
import os

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from utils.odds_provider import extract_total_for_matchup
from utils.mapping import clean_team_name

def test_match(away, home, key_list):
    print(f"\nMatch Attempt: [{away}] @ [{home}]")
    odds_data = {key: 145.5 for key in key_list}
    result = extract_total_for_matchup(odds_data, away, home)
    if result:
        print(f"  SUCCESS: Found total {result}")
    else:
        print(f"  FAILURE: Could not match")

# Actual keys from Render API
RENDER_KEYS = [
    "marshall thundering herd vs southern miss golden eagles",
    "lehigh mountain hawks vs loyola (md) greyhounds",
    "florida international golden panthers vs middle tennessee blue raiders",
    "saint mary's gaels vs san diego toreros"
]

# Cases mentioned by user
print("--- Testing User Reported Cases ---")

# 1. Mississippi vs Marshall (Southern Miss context)
test_match("Mississippi", "Marshall", RENDER_KEYS)

# 2. Lehigh vs Maryland (Loyola MD context)
test_match("Lehigh", "Maryland", RENDER_KEYS)

# 3. FIU vs Middle Tennessee
test_match("FIU", "Middle Tennessee", RENDER_KEYS)

# 4. San Diego vs Saint Mary's
test_match("San Diego", "Saint Mary's", RENDER_KEYS)

# Additional checks
print("\n--- Additional Consistency Checks ---")
print(f"Clean 'Maryland': '{clean_team_name('Maryland')}'")
print(f"Clean 'loyola (md) greyhounds': '{clean_team_name('loyola (md) greyhounds')}'")
