import json
lb = json.load(open('data/basketball/basketball_leaderboard.json', encoding='utf-8'))

for e in lb['leaderboard']:
    if 'nancy u21' in e.get('name', '').lower() or 'rimini' in e.get('name', '').lower():
        print(f"Name: {e['name']} | league_id: {e.get('league_id')}")
        print(f"  flat_floor_rate:  {e.get('flat_floor_rate')}")
        print(f"  flat_floor_hits:  {e.get('flat_floor_hits')}")
        print(f"  flat_floor_total: {e.get('flat_floor_total')}")
        print(f"  Keys: {[k for k in e.keys() if 'floor' in k or 'graded' in k]}")
        print()
