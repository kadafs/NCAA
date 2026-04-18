import json
import glob

print("1. Checking universal predictions for Israel Super League...")
league_name_target = "SUPER LEAGUE"
country_target = "ISRAEL"

total_predictions = 0
graded_predictions = 0
league_ids = set()

for f in sorted(glob.glob('data/basketball/universal_predictions_*.json')):
    try:
        with open(f, encoding='utf-8') as file:
            data = json.load(file)
            for p in data.get('predictions', []):
                if p.get('country') == country_target and p.get('league') == league_name_target:
                    total_predictions += 1
                    league_ids.add(p.get('league_id'))
                    if p.get('actual_result') is not None:
                        graded_predictions += 1
    except Exception as e:
        print(f"Error reading {f}: {e}")

print(f"Total predictions found: {total_predictions}")
print(f"Graded predictions found: {graded_predictions}")
print(f"League IDs found: {league_ids}")

print("\n2. Checking league_leaderboard.json...")
try:
    with open('data/basketball/league_leaderboard.json', encoding='utf-8') as file:
        lb = json.load(file)
        found = False
        for entry in lb:
            if "ISRAEL" in entry.get('name', '') or entry.get('league_id') in league_ids:
                print(f"Found in leaderboard: {entry['name']} (ID: {entry.get('league_id')})")
                print(f"  ADV graded: {entry.get('adv', {}).get('graded_totals', 0)}")
                print(f"  SRS graded: {entry.get('srs', {}).get('graded_totals', 0)}")
                found = True
        if not found:
            print("Not found in leaderboard.")
except Exception as e:
    print(f"Error reading leaderboard: {e}")
