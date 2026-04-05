"""
Find league IDs for the worst-offending basketball leagues.
"""
import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

TARGET_LEAGUES = [
    "1. Liga", "DBBL Women", "NBL1 Central", "Prva A Liga", "SBL",
    "LNB", "NBL1 South Women", "ABA League", "Basketligaen",
    "ZBL W", "Premijer liga", "Premier league", "FIBA Europe Cup",
    "Liga Nova KBM", "First League", "NBL1 Central Women",
    "SLB Women", "1. ZLS Women", "BSN", "Premier League W",
    "BNXT League", "Pro B", "WBL Women", "Superettan", "WKBL W"
]

found = {}

data_dir = "data/basketball"
for fname in sorted(os.listdir(data_dir), reverse=True):
    if not fname.startswith("universal_predictions_") or not fname.endswith(".json"):
        continue
    try:
        with open(os.path.join(data_dir, fname), encoding="utf-8") as f:
            data = json.load(f)
        games = data if isinstance(data, list) else data.get("predictions", [])
        for g in games:
            lname = g.get("league_name", g.get("league", ""))
            lid   = g.get("league_id")
            if lname in TARGET_LEAGUES and lid:
                found.setdefault(lname, set()).add(lid)
    except Exception:
        pass
    if len(found) >= len(TARGET_LEAGUES):
        break

print(f"\n{'LEAGUE':<35} {'ID(s)'}")
print("-" * 55)
for league in sorted(TARGET_LEAGUES):
    ids = found.get(league, set())
    print(f"  {league:<33} {', '.join(str(i) for i in ids) if ids else 'NOT FOUND'}")
