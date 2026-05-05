import json
d = json.load(open('data/basketball/universal_predictions_2026-05-06.json', encoding='utf-8'))
for p in d.get('predictions', []):
    if 'POLAND' in p.get('country', '').upper():
        print(f"{p.get('home_team')} => home_adv: {p.get('home_adv')}, away_adv: {p.get('away_adv')}")
