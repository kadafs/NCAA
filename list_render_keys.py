import requests
import json
from utils.ssl_adapter import get_robust_session

def list_keys():
    url = "https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa?date=2026-02-07"
    session = get_robust_session(retries=5)
    
    print(f"Fetching from {url}...")
    try:
        resp = session.get(url, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            keys = sorted(list(data.keys()))
            for k in keys:
                print(f"  {k}")
        else:
            print(f"Failed: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_keys()
