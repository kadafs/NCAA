import os
import sys
from datetime import datetime
import zoneinfo

# Add root to path so we can import from core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.audit_engine import fetch_ncaa_scores_espn

def test_fallback():
    date_str = "2026-02-04"
    print(f"Testing ESPN Fallback for {date_str}...")
    
    results = fetch_ncaa_scores_espn(date_str)
    
    print(f"Found {len(results)} games.")
    
    # Check for Iowa vs Washington
    # Key might vary depending on canonicalization, so checking values
    found = False
    for k, v in results.items():
        if "iowa" in k and "washington" in k:
            print(f"FOUND MATCH: {k} -> {v}")
            found = True
            
    if not found:
        print("Did not find Iowa vs Washington in fallback data.")
        # Print a few keys to see what they look like
        print("Sample keys:", list(results.keys())[:5])

if __name__ == "__main__":
    test_fallback()
