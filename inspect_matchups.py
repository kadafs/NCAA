import requests
import json
from datetime import datetime
import zoneinfo

def inspect_matchups():
    et_tz = zoneinfo.ZoneInfo("America/New_York")
    year, month, day = 2026, 2, 4
    url = f"https://ncaa-api-w2ry.onrender.com/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}"
    
    print(f"Fetching from: {url}")
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        for g_wrapper in data.get('games', []):
            g = g_wrapper.get('game')
            away = g.get('away', {}).get('names', {}).get('short', '')
            home = g.get('home', {}).get('names', {}).get('short', '')
            if "Iowa" in away or "Iowa" in home or "Washington" in away or "Washington" in home:
                print(f"MATCH: {away} vs {home}")
                print(f"  Away Names: {json.dumps(g.get('away', {}).get('names', {}))}")
                print(f"  Home Names: {json.dumps(g.get('home', {}).get('names', {}))}")
                print(f"  Scores: Away={g.get('away', {}).get('score')} | Home={g.get('home', {}).get('score')}")
                print(f"  Game State: {g.get('header', {}).get('state', {}).get('state')}")
    else:
        print(f"Failed: {r.status_code}")

if __name__ == "__main__":
    inspect_matchups()
