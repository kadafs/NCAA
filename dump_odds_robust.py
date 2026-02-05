import sys
import os
# Add root to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from utils.ssl_adapter import get_robust_session
import json

def dump_odds():
    url = "https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa"
    print(f"Fetching from: {url}")
    session = get_robust_session(retries=3)
    try:
        r = session.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            print(f"Total Keys: {len(data)}")
            for k in sorted(data.keys()):
                # Print all keys to see formatting
                print(f"KEY: '{k}'")
        else:
            print(f"Failed: {r.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_odds()
