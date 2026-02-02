import requests
import json

url_odds = "https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa"
try:
    resp = requests.get(url_odds, timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        print("KEYS FROM RENDER:")
        for k in data.keys():
            print(f"'{k}'")
except Exception as e:
    print(f"Error: {e}")
