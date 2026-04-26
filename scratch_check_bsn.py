import json, requests, os
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("API_BASKETBALL_KEY")
HEADERS = {"x-apisports-key": API_KEY}

# Check what name Cluj-Napoca uses in the API for league 78
r = requests.get("https://v1.basketball.api-sports.io/games", headers=HEADERS, params={"date": "2026-04-24", "league": 78}, timeout=20)
games = r.json().get("response", [])
print(f"=== Divizia A (78) games for 2026-04-24: {len(games)} ===")
for g in games:
    print(f"  API: '{g['teams']['home']['name']}' vs '{g['teams']['away']['name']}'")

# Check Buducnost in Montenegro league 64
r2 = requests.get("https://v1.basketball.api-sports.io/games", headers=HEADERS, params={"date": "2026-04-24", "league": 64}, timeout=20)
games2 = r2.json().get("response", [])
print(f"\n=== Prva A Liga (64) games for 2026-04-24: {len(games2)} ===")
for g in games2:
    print(f"  API: '{g['teams']['home']['name']}' vs '{g['teams']['away']['name']}'")

# Check Georgia league 39 vs 394
r3 = requests.get("https://v1.basketball.api-sports.io/games", headers=HEADERS, params={"date": "2026-04-24", "league": 39}, timeout=20)
games3 = r3.json().get("response", [])
print(f"\n=== Superleague Georgia (39) games for 2026-04-24: {len(games3)} ===")
for g in games3:
    print(f"  API: '{g['teams']['home']['name']}' vs '{g['teams']['away']['name']}' [league_id={g['league']['id']}]")
