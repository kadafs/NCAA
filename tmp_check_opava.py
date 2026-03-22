import json
d = json.load(open('data/basketball/universal_predictions_2026-03-21.json', encoding='utf-8'))
for g in d.get('predictions', []):
    if 'Opava' in g.get('home_team', '') or 'Opava' in g.get('away_team', ''):
        mc = g.get('match_center', {})
        print(f"Game: {g.get('away_team')} @ {g.get('home_team')}")
        print(f"  H2H Count: {len(mc.get('h2h', []))}")
        print(f"  RecentH Count: {len(mc.get('recentH', []))}")
        print(f"  RecentA Count: {len(mc.get('recentA', []))}")
