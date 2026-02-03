import requests
import json

url = "https://barttorvik.com/2026_team_results.json"
try:
    resp = requests.get(url, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        print(f"Total teams: {len(data)}")
        first_team = data[0]
        print("First team data indices:")
        for idx, val in enumerate(first_team):
            print(f"{idx}: {val}")
    else:
        print(f"Failed to fetch: {resp.status_code}")
except Exception as e:
    print(f"Error: {e}")
