import json

d = json.load(open('data/basketball/basketball_leaderboard.json', encoding='utf-8'))
for e in d.get('leaderboard', []):
    name = e.get('name', '')
    if 'Dabrowa' in name or 'Penarol' in name or 'Okzhetpes' in name or 'Instituto' in name:
        name_clean = name.encode('ascii', 'ignore').decode('ascii')
        print(f"{name_clean:30} | mae: {e.get('mae')} | adv_mae: {e.get('adv', {}).get('mae') if e.get('adv') else None} | srs_mae: {e.get('srs', {}).get('mae') if e.get('srs') else None}")
