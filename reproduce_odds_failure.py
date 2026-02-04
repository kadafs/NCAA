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
    "saint mary's gaels vs san diego toreros",
    "army black knights vs colgate raiders",
    "south dakota state jackrabbits vs st. thomas tommies"
]

# Cases mentioned by user
print("--- Testing User Reported Cases ---")

cases = [
    ("Mississippi", "Marshall"),
    ("Lehigh", "Maryland"),
    ("FIU", "Middle Tennessee"),
    ("San Diego", "Saint Mary's"),
    ("Army", "Colgate"),
    ("St. Thomas", "South Dakota St.")
]

for away, home in cases:
    test_match(away, home, RENDER_KEYS)

# Detailed analysis of failures
print("\n--- Detailed String Analysis ---")
def analyze(name):
    print(f"Original: '{name}' -> Clean: '{clean_team_name(name)}'")

analyze("Army")
analyze("Colgate")
analyze("St. Thomas")
analyze("South Dakota St.")
analyze("Saint Mary's")
analyze("San Diego")
analyze("army black knights vs colgate raiders")
analyze("south dakota state jackrabbits vs st. thomas tommies")
analyze("saint mary's gaels vs san diego toreros")
