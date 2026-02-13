import json
import sys
import os

# Check if D2 teams in scoreboard match teams in consolidated stats
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES

# Load D2 stats
with open("data/consolidated_stats_d2.json", "r") as f:
    stats_data = json.load(f)

# Get team names from stats
stats_teams = set(stats_data.keys())
print(f"Total teams in D2 stats: {len(stats_teams)}")
print(f"Sample team names from stats: {list(stats_teams)[:10]}\n")

# Load scoreboard
import requests
from datetime import datetime
import zoneinfo

now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
url = f"https://ncaa-api-w2ry.onrender.com/scoreboard/basketball-men/d2/{now.year}/{now.month:02d}/{now.day:02d}"
response = requests.get(url, timeout=15)
board = response.json()

print(f"Total games in scoreboard: {len(board['games'])}\n")

# Check first 5 games for team name matching
print("Checking team name matching for first 5 games:")
print("=" * 80)

for i, game_wrapper in enumerate(board['games'][:5]):
    game = game_wrapper.get('game')
    if not game: continue
    
    away_raw = game['away']['names']['short']
    home_raw = game['home']['names']['short']
    
    # Try to find teams
    nameA = find_team_in_dict(away_raw, stats_data, BASKETBALL_ALIASES)
    nameH = find_team_in_dict(home_raw, stats_data, BASKETBALL_ALIASES)
    
    print(f"\nGame {i+1}: {away_raw} @ {home_raw}")
    print(f"  Away match: {nameA if nameA else 'NOT FOUND'}")
    print(f"  Home match: {nameH if nameH else 'NOT FOUND'}")
    
    if not nameA or not nameH:
        print(f"  ⚠️ MATCH FAILED - This game will be skipped")
