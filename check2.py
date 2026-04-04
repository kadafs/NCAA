import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
with open(r'c:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\data\football\universal_predictions_2026-04-03.json', 'r', encoding='utf-8') as file:
    data = json.load(file)
for p in data.get('predictions', []):
    if 'donaufeld' in str(p.get('home_team', '')).lower() or 'donaufeld' in str(p.get('away_team', '')).lower() or 'austria' in str(p.get('country', '')).lower():
        if p.get('league') == 'Regionalliga - Ost':
            print(f"{p.get('home_team')} vs {p.get('away_team')}")
            print(f"League: {p.get('league')} | Country: {p.get('country')}")
            print(f"Actual Score: {p.get('actual_home_goals')} - {p.get('actual_away_goals')} | Status: {p.get('status')}")
            print('-'*20)
