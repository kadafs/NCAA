import json, glob, os
files = sorted(glob.glob('data/basketball/universal_predictions_*.json'))
f = files[-1]
data = json.load(open(f, encoding='utf-8'))
for p in data.get('predictions', []):
    if 'POLAND' in p.get('country', '').upper():
        print(f"{p.get('home_team')} vs {p.get('away_team')} | Fallback: {p.get('fallback_used')}")
