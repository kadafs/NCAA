import requests
from utils.ssl_adapter import get_robust_session

def test_history_endpoints():
    session = get_robust_session(retries=2)
    patterns = [
        "https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa/2026-02-07",
        "https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa?date=2026-02-07",
        "https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa?day=20260207",
        "https://ncaa-api-w2ry.onrender.com/scoreboard/basketball-men/d1/2026/02/07?odds=true"
    ]
    
    for url in patterns:
        print(f"Testing {url}...")
        try:
            resp = session.get(url, timeout=10)
            print(f" Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f" Data Type: {type(data)}")
                if isinstance(data, dict):
                    print(f" Keys: {list(data.keys())[:5]}")
                elif isinstance(data, list) and len(data) > 0:
                    print(f" First Item: {data[0]}")
        except Exception as e:
            print(f" Error: {e}")

if __name__ == "__main__":
    test_history_endpoints()
