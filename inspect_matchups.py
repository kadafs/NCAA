import requests
import json
from datetime import datetime
import zoneinfo

def inspect_matchups():
    et_tz = zoneinfo.ZoneInfo("America/New_York")
    now = datetime.now(et_tz)
    year, month, day = now.year, now.month, now.day
    url = f"https://ncaa-api-w2ry.onrender.com/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}"
    
    print(f"Fetching from: {url}")
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        for g_wrapper in data.get('games', []):
            g = g_wrapper.get('game')
            away = g.get('away', {}).get('names', {}).get('short', '')
            home = g.get('home', {}).get('names', {}).get('short', '')
            if "St. Thomas" in away or "St. Thomas" in home or "South Dakota" in away or "South Dakota" in home:
                print(f"MATCH: {away} vs {home}")
                print(f"  Away Names: {json.dumps(g.get('away', {}).get('names', {}))}")
                print(f"  Home Names: {json.dumps(g.get('home', {}).get('names', {}))}")
    else:
        print(f"Failed: {r.status_code}")

if __name__ == "__main__":
    inspect_matchups()
