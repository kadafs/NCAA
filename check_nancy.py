import json

lb = json.load(open('data/basketball/basketball_leaderboard.json', encoding='utf-8'))

print("=== Searching for Nancy entries in leaderboard ===")
for e in lb['leaderboard']:
    if 'nancy' in e.get('name', '').lower():
        print(f"  Name: '{e['name']}' | league_id: {e.get('league_id')} | mae: {e.get('mae')} | graded: {e.get('graded_totals')}")

print()
print("=== Searching for Saint Quentin entries ===")
for e in lb['leaderboard']:
    if 'saint quentin' in e.get('name', '').lower() or 'quentin' in e.get('name', '').lower():
        print(f"  Name: '{e['name']}' | league_id: {e.get('league_id')} | mae: {e.get('mae')} | graded: {e.get('graded_totals')}")
