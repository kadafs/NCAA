import requests
from datetime import datetime
import zoneinfo

# Test D2 scoreboard fetch
now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
year, month, day = now.year, now.month, now.day

url = f"https://ncaa-api-w2ry.onrender.com/scoreboard/basketball-men/d2/{year}/{month:02d}/{day:02d}"
print(f"Testing URL: {url}")

try:
    response = requests.get(url, timeout=15)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nResponse keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
        
        if 'games' in data:
            print(f"Number of games: {len(data['games'])}")
            if data['games']:
                print(f"\nFirst game sample:")
                print(data['games'][0])
        else:
            print(f"\nFull response: {data}")
    else:
        print(f"Error response: {response.text[:500]}")
except Exception as e:
    print(f"Exception: {e}")
