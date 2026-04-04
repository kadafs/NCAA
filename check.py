import json
with open(r'c:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\data\football\universal_predictions_2026-04-03.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
for p in data.get('predictions', []):
    league = str(p.get('league_name', '')).lower()
    if 'regionalliga' in league or 'donaufeld' in str(p).lower():
        print(f"{p.get('league_name')} - {p.get('home_team', {}).get('name')} vs {p.get('away_team', {}).get('name')}")
        print(f"Scores: None" if p.get('fixture', {}) is None else f"Scores: {p.get('fixture', {}).get('goalsHome')} - {p.get('fixture', {}).get('goalsAway')}")
        print(f"Status: None" if p.get('fixture', {}) is None else f"Status: {p.get('fixture', {}).get('statusShort')}")
        print('-'*20)
