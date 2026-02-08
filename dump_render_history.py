import requests
import json
from utils.ssl_adapter import get_robust_session

def dump_render_history():
    url = "https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa?date=2026-02-07"
    session = get_robust_session(retries=2)
    
    print(f"Fetching from {url}...")
    try:
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            print(f"Found {len(data)} entries.")
            
            # Count variety
            totals = list(data.values())
            unique_totals = set(totals)
            print(f"Unique Totals: {len(unique_totals)}")
            
            # Sample some
            it = iter(data.items())
            for i in range(10):
                k, v = next(it)
                print(f"  {k}: {v}")
                
            if 145.5 in unique_totals:
                count_145 = totals.count(145.5)
                print(f"Count of 145.5: {count_145}")
        else:
            print(f"Failed: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_render_history()
