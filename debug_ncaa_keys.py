import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.audit_engine import fetch_ncaa_scores_espn
from utils.mapping import clean_team_name

def debug_keys():
    date_str = "2026-02-04"
    print(f"--- Fetching ESPN Scores for {date_str} ---")
    results = fetch_ncaa_scores_espn(date_str)
    
    print(f"\nFound {len(results)} games. Listing keys:")
    for key in sorted(results.keys()):
        print(f"Result Key: {key}")

if __name__ == "__main__":
    debug_keys()
