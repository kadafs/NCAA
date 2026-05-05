import os, json

print("=== Searching advanced metrics ===")
found_adv = False
for root, dirs, files in os.walk('data'):
    for file in files:
        if file.startswith('bball_stats_') and file.endswith('_adv.json'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for team, stats in data.items():
                    if 'Cocodrilos' in team or 'Panteras' in team or 'Trotamundos' in team:
                        print(f"Found {team} in {file} - Matches: {stats.get('matches_played')}, Vol: {stats.get('std_dev_totals')}")
                        found_adv = True
            except:
                pass
if not found_adv:
    print("Not found in advanced metrics.")

print("\n=== Searching predictions ===")
found_pred = False
for root, dirs, files in os.walk('data'):
    for file in files:
        if file.startswith('universal_predictions_'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for game in data:
                    h_team = game.get('home_team', '')
                    a_team = game.get('away_team', '')
                    if 'Cocodrilos' in h_team or 'Panteras' in h_team or 'Trotamundos' in h_team or \
                       'Cocodrilos' in a_team or 'Panteras' in a_team or 'Trotamundos' in a_team:
                        print(f"Found in {file}: {h_team} vs {a_team} - Home Volatility: {game.get('home_team_volatility')}")
                        found_pred = True
            except:
                pass
if not found_pred:
    print("Not found in predictions.")
