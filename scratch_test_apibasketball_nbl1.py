import requests, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv('API_BASKETBALL_KEY')
headers = {'x-apisports-key': key}

# Check what seasons exist for NBL1 South (209)
url = 'https://v1.basketball.api-sports.io/seasons'
res = requests.get(url, headers=headers)
seasons = res.json().get('response', [])
print(f"Available seasons: {seasons[:20]}")
print()

# Also try just league 209 with no season filter
url2 = 'https://v1.basketball.api-sports.io/games'
for season in ['2026', '2025', '2024-2025', '2025-2026']:
    res = requests.get(url2, headers=headers, params={'league': 209, 'season': season})
    count = len(res.json().get('response', []))
    print(f"  Season '{season}': {count} games")
