"""
explore_api_basketball_today.py
================================
Queries api-basketball.com /games for today's date and lists ALL leagues
that have games, with game counts and sample matchups.

Also checks /leagues to understand what's available in general.
"""
import io
import sys
import os
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

load_dotenv()

API_KEY = os.getenv("API_BASKETBALL_KEY")
BASE_URL = "https://v1.basketball.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

ET_TZ = ZoneInfo("America/New_York")
today = datetime.now(ET_TZ).strftime("%Y-%m-%d")

print(f"\n{'='*70}")
print(f"  api-basketball.com  |  ALL GAMES for {today}")
print(f"{'='*70}\n")

# ── Check remaining API credits first ──────────────────────────────────────
status_resp = requests.get(f"{BASE_URL}/status", headers=HEADERS, timeout=10)
status_data = status_resp.json().get("response", {})
account = status_data.get("account", {})
requests_left = status_data.get("requests", {})
print(f"  Account  : {account.get('firstname', '')} {account.get('lastname', '')} ({account.get('email', '')})")
print(f"  Plan     : {account.get('plan', 'unknown')}")
print(f"  API Calls: {requests_left.get('current', '?')} used / {requests_left.get('limit_day', '?')} daily limit")
print()

# ── Fetch ALL games for today (single request) ─────────────────────────────
print(f"  Fetching all games for {today}...")
resp = requests.get(
    f"{BASE_URL}/games",
    headers=HEADERS,
    params={"date": today},
    timeout=15,
)
raw = resp.json()
all_games = raw.get("response", [])
total = raw.get("results", 0)

print(f"  Total games returned: {total}\n")

if not all_games:
    print("  No games found for today.")
    sys.exit(0)

# ── Group by league ────────────────────────────────────────────────────────
from collections import defaultdict
by_league = defaultdict(list)

for game in all_games:
    league = game.get("league", {})
    lid    = league.get("id")
    lname  = league.get("name", "Unknown")
    ltype  = league.get("type", "")
    country_obj = game.get("country", {})
    country = country_obj.get("name", "")
    season = game.get("season")

    home = game.get("teams", {}).get("home", {}).get("name", "?")
    away = game.get("teams", {}).get("away", {}).get("name", "?")
    status_long = game.get("status", {}).get("long", "Scheduled")
    game_date = game.get("date", "")[:16].replace("T", " ")

    hs = game.get("scores", {}).get("home", {}).get("total")
    as_ = game.get("scores", {}).get("away", {}).get("total")
    score = f"{as_}-{hs}" if hs is not None and as_ is not None else ""

    by_league[(lid, lname, ltype, country, season)].append({
        "home": home,
        "away": away,
        "time": game_date,
        "status": status_long,
        "score": score,
    })

# ── Print sorted by league name ────────────────────────────────────────────
sorted_leagues = sorted(by_league.items(), key=lambda x: x[0][1])

for (lid, lname, ltype, country, season), games in sorted_leagues:
    flag = f"[{country}]" if country else ""
    print(f"  [{lid:>4}] {lname:45} {flag:25} Season:{season}  ({len(games)} game{'s' if len(games)!=1 else ''})")
    # Show up to 3 sample games per league
    for g in games[:3]:
        score_str = f"  {g['score']}" if g['score'] else ""
        status_str = f"  [{g['status']}]" if g['status'] not in ("Game Scheduled", "Scheduled", "") else ""
        print(f"         {g['away']:30} @ {g['home']:30}  {g['time']}{status_str}{score_str}")
    if len(games) > 3:
        print(f"         ... and {len(games)-3} more games")
    print()

print(f"{'='*70}")
print(f"  TOTAL: {total} games across {len(by_league)} league(s) on {today}")
print(f"{'='*70}\n")

# ── Save full raw data ─────────────────────────────────────────────────────
os.makedirs("data", exist_ok=True)
out = {
    "date": today,
    "total_games": total,
    "leagues_summary": [
        {
            "league_id": lid,
            "league_name": lname,
            "type": ltype,
            "country": country,
            "season": season,
            "game_count": len(games),
            "games": games,
        }
        for (lid, lname, ltype, country, season), games in sorted_leagues
    ]
}
with open(f"data/api_basketball_today_{today}.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print(f"  Full data saved -> data/api_basketball_today_{today}.json\n")
