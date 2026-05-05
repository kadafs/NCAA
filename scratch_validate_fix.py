import sys
sys.path.insert(0, '.')
from scrape_nbl1 import extract_box_score

confirmed_uuids = [
    "9169cd45-d6e8-11f0-a9c0-cfb7d5472bba",  # 2026-04-24
    "6af07794-d3dd-11f0-a3df-056d5acb892b",  # 2026-04-02
    "2422f919-da64-11f0-8a63-1f4631345f86",  # 2026-05-02
]

for uid in confirmed_uuids:
    result = extract_box_score(uid)
    if result:
        home = result['home_team']
        away = result['away_team']
        date = result['date']
        league = result['competition']
        hp = len(result['stats']['home']['players'])
        ap = len(result['stats']['away']['players'])
        print(f"SUCCESS: {home} vs {away} ({date}) [{league}] - {hp} home players, {ap} away players")
    else:
        print(f"FAILED: {uid}")
