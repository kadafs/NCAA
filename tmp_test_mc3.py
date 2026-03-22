import json

d = json.load(open('data/basketball/universal_predictions_2026-03-21.json', encoding='utf-8'))
found_h2h = 0
found_recent = 0

for g in d.get('predictions', []):
    mc = g.get('match_center', {})
    if len(mc.get('h2h', [])) > 0: found_h2h += 1
    if len(mc.get('recentH', [])) > 0: found_recent += 1

print(f"Games with offline H2H: {found_h2h}")
print(f"Games with offline Recent Form: {found_recent}")

for g in d.get('predictions', []):
    mc = g.get('match_center', {})
    if len(mc.get('recentH', [])) > 0:
        print(f"\nSample Game: {g.get('away_team')} @ {g.get('home_team')}")
        print(f"  H2H Count: {len(mc.get('h2h', []))}")
        print(f"  Recent Form Count: {len(mc.get('recentH', []))}")
        break
