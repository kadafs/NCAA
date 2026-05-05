"""
Diagnose how many teams in fixture predictions are NOT found in the leaderboard.
"""
import json, sys, os, difflib
sys.path.append(os.path.abspath('.'))
from run_confidence_report import load_leaderboard, lookup_team

DATE = "2026-05-05"
pred_path = f"data/basketball/universal_predictions_{DATE}.json"

preds = json.load(open(pred_path, encoding="utf-8"))["predictions"]
lb = load_leaderboard()

found = []
missing = []

for p in preds:
    lid   = p.get("league_id")
    home  = p.get("home_team", "?")
    away  = p.get("away_team", "?")

    for team in [home, away]:
        entry = lookup_team(team, lid, lb)
        if entry:
            found.append((team, lid, p.get("league")))
        else:
            missing.append((team, lid, p.get("league")))

print(f"Found:   {len(found)}")
print(f"Missing: {len(missing)}")
print(f"\nMissing teams (sample of 30):")
for t, lid, league in missing[:30]:
    print(f"  {t:30}  [lid:{lid}]  {league}")

# Check leaderboard names for a specific league to understand the mismatch
print("\n\nLeaderboard names for league 72 (Poland):")
for (name, l), entry in lb.items():
    if l == 72:
        print(f"  {name}")
