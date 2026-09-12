import json, sys
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('data/football/universal_39_stats.json', 'r', encoding='utf-8'))
for team, s in data['teams'].items():
    if 'Aston Villa' in team or 'Nottingham' in team:
        print(f"=== {team} ===")
        print(json.dumps(s, indent=2))
