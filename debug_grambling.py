import os
import sys
# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.audit_engine import fetch_ncaa_scores_espn, get_canonical_key

def inspect_grambling():
    date_str = "2026-02-04"
    print(f"Fetching ESPN scores for {date_str}...")
    results = fetch_ncaa_scores_espn(date_str)
    
    print("\nSearching for Grambling or Pine Bluff matches...")
    for key, val in results.items():
        if "gramb" in key or "pine" in key or "ark" in key:
            print(f"Found Key: '{key}' -> {val}")

if __name__ == "__main__":
    inspect_grambling()
