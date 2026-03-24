import json

with open('data/basketball/universal_predictions_2026-03-23.json', encoding='utf-8') as f:
    data = json.load(f)

targets = [
    ('Zadar', 'Studentski'),
    ('Neptunas', 'Telsiai'),
    ('Jurbarkas', 'Mazeikiai'),
]

for p in data['predictions']:
    ht = p.get('home_team','').lower()
    at = p.get('away_team','').lower()
    for h, a in targets:
        if h.lower() in ht or a.lower() in at or h.lower() in at or a.lower() in ht:
            print(f"{p.get('home_team')} vs {p.get('away_team')} | league={p.get('league')} | league_id={p.get('league_id')} | arch={p.get('model_architecture')}")
            break
