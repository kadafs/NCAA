import json

# Check ABA (198) team name matching
print("=== ABA League (198) ===")
with open('data/bball_stats_198_adv.json', encoding='utf-8') as f:
    adv = json.load(f)
adv_teams = {t['team_name'] for t in adv.get('teams', [])}
print(f"ADV file teams ({len(adv_teams)}): {sorted(adv_teams)}")

# Check games from prediction file
with open('data/basketball/universal_predictions_2026-03-23.json', encoding='utf-8') as f:
    preds = json.load(f)

aba_games = [(p['home_team'], p['away_team']) for p in preds['predictions'] if p.get('league_id') == 198]
unique_aba = list({g for g in aba_games})
print(f"\nABA games in prediction file: {unique_aba[:5]}")
for home, away in unique_aba[:3]:
    hm = home in adv_teams
    am = away in adv_teams
    print(f"  {home} ({hm}) vs {away} ({am})")

# Check NKL (61)
print("\n=== NKL (61) ===")
try:
    with open('data/bball_stats_61_adv.json', encoding='utf-8') as f:
        adv61 = json.load(f)
    nkl_teams = {t['team_name'] for t in adv61.get('teams', [])}
    print(f"NKL ADV teams: {sorted(nkl_teams)[:5]}")
except Exception as e:
    print(f"ERROR reading NKL ADV: {e}")
