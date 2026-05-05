import requests, json, re
from datetime import datetime

SPORTRADAR_URL = "https://embed-api.eui.connect.sportradar.com/v1/embed/3/fixture_detail?fixtureId={}"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36',
    'Referer': 'https://nbl1.com.au/',
}

COMPETITION_MAP = {
    "NBL1 South Men": 209, "NBL1 South Women": 210,
    "NBL1 North Men": 207, "NBL1 North Women": 208,
    "NBL1 East Men": 215, "NBL1 East Women": 216,
    "NBL1 Central Men": 212, "NBL1 Central Women": 211,
    "NBL1 West Men": 214, "NBL1 West Women": 213,
}

uid = "6af07794-d3dd-11f0-a3df-056d5acb892b"
print(f"Testing: {uid}")

try:
    res = requests.get(SPORTRADAR_URL.format(uid), headers=HEADERS, timeout=15)
    print(f"HTTP status: {res.status_code}")
except Exception as e:
    print(f"Request FAILED: {e}")
    exit()

try:
    raw = res.json()
    data = raw.get("data", {})
except Exception as e:
    print(f"JSON parse FAILED: {e}")
    exit()

banner = data.get("banner", {})
fixture_meta = banner.get("fixture", {})
competition = banner.get("competition", {})
competitors = fixture_meta.get("competitors", [])

if not competition or not competition.get("name"):
    print("FAIL: no competition name")
    exit()

comp_name = competition.get("name")
print(f"Competition: {comp_name}")

if comp_name not in COMPETITION_MAP:
    print(f"FAIL: '{comp_name}' not in COMPETITION_MAP")
    exit()

home_team = next((c.get("name") for c in competitors if c.get("isHome")), None)
away_team = next((c.get("name") for c in competitors if not c.get("isHome")), None)
print(f"Teams: {home_team} vs {away_team}")

fixture_top = data.get("fixture", {})
status = fixture_top.get("status", "").upper()
print(f"Status: {status}")

completed_statuses = {"CONFIRMED", "CLOSED", "PLAYED", "ENDED", "FINAL", "FT", "AOT"}
if status not in completed_statuses:
    print(f"FAIL: status '{status}' not in completed_statuses")
    exit()

date_str = fixture_top.get("startTimeLocal") or fixture_top.get("startTimeUTC")
print(f"Date string: {date_str}")

stats_base = data.get("statistics", {}).get("data", {}).get("base", {})
print(f"stats_base exists: {bool(stats_base)}")

home_data = stats_base.get("home", {})
away_data = stats_base.get("away", {})

def get_players(side_data):
    players = []
    for group in side_data.get("persons", []):
        for row in group.get("rows", []):
            s = row.get("statistics", {})
            mins = s.get("minutes", "")
            participated = row.get("participated", True)
            if not mins or not participated:
                continue
            players.append(row.get("personName", "Unknown"))
    return players

hp = get_players(home_data)
ap = get_players(away_data)
print(f"Home players: {len(hp)}")
print(f"Away players: {len(ap)}")

if not hp or not ap:
    print("FAIL: no players extracted")
else:
    print(f"SUCCESS! Game extracted. {home_team} vs {away_team}")
