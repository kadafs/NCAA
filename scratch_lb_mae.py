import json
d = json.load(open('data/basketball/basketball_leaderboard.json', encoding='utf-8'))
lb = d.get('leaderboard', [])
no_mae = [e for e in lb if not e.get('mae')]
print(f"Total entries: {len(lb)}")
print(f"Entries with no MAE: {len(no_mae)}")
for e in no_mae[:10]:
    name = e.get('name', 'Unknown').encode('ascii', 'ignore').decode('ascii')
    print(f"  {name:30} | graded: {e.get('graded_totals')} | {e.get('league')}")
